package com.papermind.backend.controller;

import com.papermind.backend.common.ApiResponse;
import com.papermind.backend.common.BizException;
import com.papermind.backend.common.ErrorCode;
import com.papermind.backend.service.ArxivClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.data.redis.core.StringRedisTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.time.Duration;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@RestController
@RequestMapping("/api/search")
public class SearchController {

    private static final Logger log = LoggerFactory.getLogger(SearchController.class);

    private final ArxivClient arxivClient;
    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;

    public SearchController(ArxivClient arxivClient,
                            StringRedisTemplate redis,
                            ObjectMapper objectMapper) {
        this.arxivClient = arxivClient;
        this.redis = redis;
        this.objectMapper = objectMapper;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> search(
        @RequestParam(required = false) String keyword,
        @RequestParam(defaultValue = "arxiv") String source,
        @RequestParam(defaultValue = "1") int page,
        @RequestParam(defaultValue = "10") int size) {

        if (keyword == null || keyword.trim().isEmpty()) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }
        if (page < 1 || size < 1 || size > 50) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }
        if (!"arxiv".equals(source)) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }

        String key = cacheKey(source, keyword.trim());
        int start = (page - 1) * size;
        boolean degraded = false;

        // 1. 先查缓存：命中直接返回，不联网
        Map<String, Object> cachedData = readCache(key);
        if (cachedData != null) {
            return ApiResponse.ok(cachedData);
        }

        // 2. 缓存没有，调 arXiv
        Map<String, Object> data = new HashMap<>();
        try {
            ArxivClient.Result result = arxivClient.search(keyword.trim(), start, size);
            data.put("total", result.total);
            data.put("items", result.items);
            writeCache(key, result);
        } catch (IllegalArgumentException e) {
            log.error("arxiv URL 非法 keyword={}", keyword, e);
            throw new BizException(ErrorCode.INTERNAL_ERROR);
        } catch (java.net.http.HttpTimeoutException e) {
            log.warn("arxiv 检索超时 keyword={}", keyword, e);
            degraded = true;
            data.put("total", 0);
            data.put("items", List.of());
        } catch (Exception e) {
            log.error("arxiv 检索失败 keyword={}", keyword, e);
            degraded = true;
            data.put("total", 0);
            data.put("items", List.of());
        }

        data.put("degraded", degraded);
        data.put("cached", false);
        if (degraded) {
            data.put("message", "外部数据源不可用");
        }

        return ApiResponse.ok(data);
    }


    private String cacheKey(String source, String keyword) {
        return "search:" + source + ":" + Integer.toHexString(keyword.hashCode());
    }

    private Map<String, Object> readCache(String key) {
        try {
            String json = redis.opsForValue().get(key);
            if (json == null) {
                return null;
            }
            Map<String, Object> cached = objectMapper.readValue(json, new TypeReference<Map<String, Object>>() {});
            Map<String, Object> data = new HashMap<>();
            data.put("total", cached.get("total"));
            data.put("items", cached.get("items"));
            data.put("cached", true);
            data.put("message", "离线缓存（更新时间 " + cached.get("cachedAt") + "）");
            return data;
        } catch (Exception e) {
            log.warn("读缓存失败 key={}", key, e);
            return null;
        }
    }

    private void writeCache(String key, ArxivClient.Result result) {
        try {
            Map<String, Object> value = new HashMap<>();
            value.put("total", result.total);
            value.put("items", result.items);
            value.put("cachedAt", LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
            redis.opsForValue().set(key, objectMapper.writeValueAsString(value), Duration.ofHours(24));
        } catch (Exception e) {
            log.warn("写缓存失败 key={}", key, e);
        }
    }

}
