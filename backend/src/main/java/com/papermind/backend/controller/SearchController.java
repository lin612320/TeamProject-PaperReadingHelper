package com.papermind.backend.controller;

import com.papermind.backend.common.ApiResponse;
import com.papermind.backend.common.BizException;
import com.papermind.backend.common.ErrorCode;
import com.papermind.backend.service.ArxivClient;
import com.papermind.backend.service.OpenAlexClient;
import com.papermind.backend.service.SearchMerger;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.Duration;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;

@RestController
@RequestMapping("/api/search")
public class SearchController {

    private static final Logger log = LoggerFactory.getLogger(SearchController.class);

    private static final ZoneId ZONE = ZoneId.of("Asia/Shanghai");
    private static final DateTimeFormatter TIME_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    /** 每个源最多取多少条参与合并 */
    private static final int FETCH_CAP = 100;

    private static final String MODE_ALL = "all";
    private static final String MODE_ARXIV = "arxiv";
    private static final String MODE_OPENALEX = "openalex";

    private final ArxivClient arxivClient;
    private final OpenAlexClient openAlexClient;
    private final StringRedisTemplate redis;
    private final ObjectMapper objectMapper;
    private final Executor searchExecutor;

    public SearchController(ArxivClient arxivClient,
                            OpenAlexClient openAlexClient,
                            StringRedisTemplate redis,
                            ObjectMapper objectMapper,
                            @Qualifier("searchExecutor") Executor searchExecutor) {
        this.arxivClient = arxivClient;
        this.openAlexClient = openAlexClient;
        this.redis = redis;
        this.objectMapper = objectMapper;
        this.searchExecutor = searchExecutor;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> search(
        @RequestParam(required = false) String keyword,
        @RequestParam(required = false) String source,
        @RequestParam(defaultValue = "1") int page,
        @RequestParam(defaultValue = "10") int size) {

        if (keyword == null || keyword.trim().isEmpty()) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }
        if (page < 1 || size < 1 || size > 50) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }

        String mode = normalizeSource(source);
        String kw = keyword.trim();

        if (page > 1) {
            log.debug("检索分页参数已废弃，按第一页处理 keyword={} page={}", kw, page);
        }

        String key = cacheKey(mode, kw, size);
        CachedHit hit = readCache(key);
        if (hit != null) {
            return ApiResponse.ok(hit.data, "离线缓存（更新时间 " + hit.cachedAt + "）");
        }

        if (!MODE_ALL.equals(mode)) {
            int count = Math.min(size, FETCH_CAP);
            Fetch fetch = MODE_ARXIV.equals(mode) ? fetchArxiv(kw, count) : fetchOpenAlex(kw, count);
            return singleSourceResponse(mode, key, fetch, size);
        }

        int fetchEach = Math.min(size * 2, FETCH_CAP);
        return mergedResponse(key, kw, fetchEach, size);
    }

    private ApiResponse<Map<String, Object>> singleSourceResponse(String mode, String key, Fetch fetch, int size) {
        Map<String, Object> data = new HashMap<>();
        if (fetch.error != null) {
            log.error("{} 检索失败", mode, fetch.error);
            data.put("total", 0);
            data.put("items", List.of());
            data.put("degraded", true);
            data.put("cached", false);
            return ApiResponse.ok(data, "外部数据源不可用，请稍后重试");
        }

        List<Map<String, Object>> items = fetch.items;
        if (items.size() > size) {
            items = new ArrayList<>(items.subList(0, size));
        }

        data.put("total", fetch.total);
        data.put("items", items);
        data.put("degraded", false);
        data.put("cached", false);
        writeCache(key, fetch.total, items);
        return ApiResponse.ok(data);
    }

    private ApiResponse<Map<String, Object>> mergedResponse(String key, String keyword, int fetchEach, int size) {
        CompletableFuture<Fetch> arxivFuture =
            CompletableFuture.supplyAsync(() -> fetchArxiv(keyword, fetchEach), searchExecutor);
        CompletableFuture<Fetch> openAlexFuture =
            CompletableFuture.supplyAsync(() -> fetchOpenAlex(keyword, fetchEach), searchExecutor);

        Fetch arxiv = arxivFuture.join();
        Fetch openAlex = openAlexFuture.join();

        Map<String, Object> data = new HashMap<>();

        if (arxiv.error != null && openAlex.error != null) {
            log.error("两源检索均失败 keyword={}", keyword, arxiv.error);
            data.put("total", 0);
            data.put("items", List.of());
            data.put("degraded", true);
            data.put("cached", false);
            return ApiResponse.ok(data, "外部数据源不可用，请稍后重试");
        }

        List<Map<String, Object>> pool =
            SearchMerger.merge(arxiv.items, openAlex.items, Integer.MAX_VALUE);
        int total = pool.size();
        List<Map<String, Object>> items = pool.size() > size
            ? new ArrayList<>(pool.subList(0, size))
            : pool;

        data.put("total", total);
        data.put("items", items);
        data.put("degraded", false);
        data.put("cached", false);

        if (arxiv.error != null) {
            log.warn("arXiv 检索失败，已返回 OpenAlex 结果 keyword={}", keyword, arxiv.error);
            return ApiResponse.ok(data, "arXiv 暂不可用，已返回 OpenAlex 结果");
        }
        if (openAlex.error != null) {
            log.warn("OpenAlex 检索失败，已返回 arXiv 结果 keyword={}", keyword, openAlex.error);
            return ApiResponse.ok(data, "OpenAlex 暂不可用，已返回 arXiv 结果");
        }

        writeCache(key, total, items);
        return ApiResponse.ok(data);
    }

    private Fetch fetchArxiv(String keyword, int count) {
        Fetch fetch = new Fetch();
        try {
            ArxivClient.Result result = arxivClient.search(keyword, 0, count);
            fetch.items = result.items;
            fetch.total = result.total;
        } catch (Exception e) {
            fetch.error = e;
        }
        return fetch;
    }

    private Fetch fetchOpenAlex(String keyword, int count) {
        Fetch fetch = new Fetch();
        try {
            OpenAlexClient.Result result = openAlexClient.search(keyword, 1, count);
            fetch.items = result.items;
            fetch.total = result.total;
        } catch (Exception e) {
            fetch.error = e;
        }
        return fetch;
    }

    private String normalizeSource(String source) {
        if (source == null || source.trim().isEmpty()) {
            return MODE_ALL;
        }
        String value = source.trim().toLowerCase();
        if (MODE_ALL.equals(value) || MODE_ARXIV.equals(value) || MODE_OPENALEX.equals(value)) {
            return value;
        }
        throw new BizException(ErrorCode.INVALID_PARAM);
    }

    private static class Fetch {
        List<Map<String, Object>> items = new ArrayList<>();
        int total;
        Exception error;
    }

    private static class CachedHit {
        Map<String, Object> data;
        String cachedAt;
    }

    private String cacheKey(String mode, String keyword, int size) {
        return "search:pool:" + mode + ":" + Integer.toHexString(keyword.hashCode()) + ":s" + size;
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
