package com.papermind.backend.controller;

import com.papermind.backend.common.ApiResponse;
import com.papermind.backend.common.BizException;
import com.papermind.backend.common.ErrorCode;
import com.papermind.backend.service.ArxivClient;
import com.papermind.backend.service.OpenAlexClient;
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
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;

@RestController
@RequestMapping("/api/search")
public class SearchController {

    private static final Logger log = LoggerFactory.getLogger(SearchController.class);

    private static final ZoneId ZONE = ZoneId.of("Asia/Shanghai");
    private static final DateTimeFormatter TIME_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private final ArxivClient arxivClient;
    private final OpenAlexClient openAlexClient;
    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;

    public SearchController(ArxivClient arxivClient,
                            OpenAlexClient openAlexClient,
                            StringRedisTemplate redis,
                            ObjectMapper objectMapper) {
        this.arxivClient = arxivClient;
        this.openAlexClient = openAlexClient;
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
        if (!"arxiv".equals(source) && !"openalex".equals(source)) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }

        String key = cacheKey(source, keyword.trim(), page, size);
        int start = (page - 1) * size;

        CachedHit hit = readCache(key);
        if (hit != null) {
            return ApiResponse.ok(hit.data, "离线缓存（更新时间 " + hit.cachedAt + "）");
        }

        Map<String, Object> data = new HashMap<>();
        boolean degraded = false;
        try {
            if ("openalex".equals(source)) {
                OpenAlexClient.Result result = openAlexClient.search(keyword.trim(), page, size);
                data.put("total", result.total);
                data.put("items", result.items);
                writeCache(key, result.total, result.items);
            } else {
                ArxivClient.Result result = arxivClient.search(keyword.trim(), start, size);
                data.put("total", result.total);
                data.put("items", result.items);
                writeCache(key, result.total, result.items);
            }
        } catch (IllegalArgumentException e) {
            log.error("arxiv URL 非法 keyword={}", keyword, e);
            throw new BizException(ErrorCode.INTERNAL_ERROR);
        } catch (Exception e) {
            // arXiv 挂了（限流 429 / 超时 / 连接失败）就回落 OpenAlex，
            // 别让用户在检索页干等半分钟再拿到一个空列表。
            // 注意：只对默认源（arxiv）兜底；用户显式指定 source=openalex 时它本来就是 OpenAlex。
            if ("arxiv".equals(source)) {
                log.warn("arxiv 不可用（{}），回落 OpenAlex keyword={}", e.toString(), keyword);
                try {
                    OpenAlexClient.Result fallback = openAlexClient.search(keyword.trim(), page, size);
                    data.put("total", fallback.total);
                    data.put("items", fallback.items);
                    writeCache(key, fallback.total, fallback.items);
                    data.put("degraded", false);
                    data.put("cached", false);
                    return ApiResponse.ok(data, "arXiv 暂时不可用，已切换到 OpenAlex");
                } catch (Exception e2) {
                    log.error("OpenAlex 兜底也失败 keyword={}", keyword, e2);
                }
            } else {
                log.error("openalex 检索失败 keyword={}", keyword, e);
            }
            degraded = true;
            data.put("total", 0);
            data.put("items", List.of());
        }

        data.put("degraded", degraded);
        data.put("cached", false);

        if (degraded) {
            return ApiResponse.ok(data, "外部数据源不可用，请稍后重试");
        }
        return ApiResponse.ok(data);
    }

    private static class CachedHit {
        Map<String, Object> data;
        String cachedAt;
    }

    private String cacheKey(String source, String keyword, int page, int size) {
        return "search:" + source + ":" + Integer.toHexString(keyword.hashCode())
            + ":p" + page + ":s" + size;
    }

    private CachedHit readCache(String key) {
        try {
            String json = redis.opsForValue().get(key);
            if (json == null) {
                return null;
            }
            Map<String, Object> cached = objectMapper.readValue(
                json, new TypeReference<Map<String, Object>>() {
                });

            CachedHit hit = new CachedHit();
            Map<String, Object> data = new HashMap<>();
            data.put("total", cached.get("total"));
            data.put("items", cached.get("items"));
            data.put("cached", true);
            data.put("degraded", false);
            hit.data = data;
            hit.cachedAt = cached.get("cachedAt") == null ? "未知" : String.valueOf(cached.get("cachedAt"));
            return hit;
        } catch (Exception e) {
            log.warn("读缓存失败 key={}", key, e);
            return null;
        }
    }

    private void writeCache(String key, int total, List<Map<String, Object>> items) {
        try {
            Map<String, Object> value = new HashMap<>();
            value.put("total", total);
            value.put("items", items);
            value.put("cachedAt", ZonedDateTime.now(ZONE).format(TIME_FMT));
            redis.opsForValue().set(key, objectMapper.writeValueAsString(value), Duration.ofHours(24));
        } catch (Exception e) {
            log.warn("写缓存失败 key={}", key, e);
        }
    }
}
