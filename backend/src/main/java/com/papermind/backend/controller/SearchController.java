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

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/search")
public class SearchController {

    private static final Logger log = LoggerFactory.getLogger(SearchController.class);

    private final ArxivClient arxivClient;

    public SearchController(ArxivClient arxivClient) {
        this.arxivClient = arxivClient;
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

        Map<String, Object> data = new HashMap<>();
        int start = (page - 1) * size;

        try {
            ArxivClient.Result result = arxivClient.search(keyword.trim(), start, size);
            data.put("total", result.total);
            data.put("items", result.items);
        } catch (IllegalArgumentException e) {
            log.error("arxiv URL 非法 keyword={}", keyword, e);
            throw new BizException(ErrorCode.INTERNAL_ERROR);
        } catch (java.net.http.HttpTimeoutException e) {
            log.warn("arxiv 检索超时 keyword={}", keyword, e);
            data.put("total", 0);
            data.put("items", List.of());
        } catch (Exception e) {
            log.error("arxiv 检索失败 keyword={}", keyword, e);
            data.put("total", 0);
            data.put("items", List.of());
        }

        return ApiResponse.ok(data);
    }
}
