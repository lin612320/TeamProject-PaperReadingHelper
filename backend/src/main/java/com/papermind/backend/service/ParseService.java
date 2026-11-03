package com.papermind.backend.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@Service
public class ParseService {

    private static final Logger log = LoggerFactory.getLogger(ParseService.class);

    private final JdbcTemplate jdbcTemplate;
    private final RestTemplate restTemplate;

    @Value("${app.parse.mock:true}")
    private boolean mock;

    /** 是否强制重建已有切片（契约 force 字段），默认 false */
    @Value("${app.parse.force:false}")
    private boolean force;

    @Value("${app.ai-service.url:http://localhost:8000}")
    private String aiServiceUrl;

    public ParseService(JdbcTemplate jdbcTemplate, RestTemplate restTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        this.restTemplate = restTemplate;
    }

    @Async
    public void parseAsync(Long paperId, String filePath) {
        log.info("parse start paperId={} mock={} thread={}",
                paperId, mock, Thread.currentThread().getName());
        try {
            jdbcTemplate.update(
                "UPDATE papers SET parse_status = 'parsing', parse_error = NULL WHERE id = ?", paperId);

            int pageCount;
            int chunkCount;

            if (mock) {
                Thread.sleep(3000);
                pageCount = 15;
                chunkCount = 128;
            } else {
                Map<String, Object> req = new HashMap<>();
                req.put("paperId", paperId);
                req.put("filePath", filePath);
                req.put("force", force);

                ResponseEntity<Map> resp = restTemplate.postForEntity(
                    aiServiceUrl + "/internal/papers/parse", req, Map.class);

                Map<?, ?> body = resp.getBody();
                if (body == null) {
                    throw new IllegalStateException("AI 服务返回空响应");
                }
                pageCount = ((Number) body.get("pageCount")).intValue();
                chunkCount = ((Number) body.get("chunkCount")).intValue();
            }

            jdbcTemplate.update(
                "UPDATE papers SET parse_status = 'ready', page_count = ?, chunk_count = ? WHERE id = ?",
                pageCount, chunkCount, paperId);

        } catch (Exception e) {
            log.error("parse failed, paperId={}", paperId, e);
            String msg = e.getMessage() == null ? "unknown error" : e.getMessage();
            if (msg.length() > 500) {
                msg = msg.substring(0, 500);
            }
            jdbcTemplate.update(
                "UPDATE papers SET parse_status = 'failed', parse_error = ? WHERE id = ?",
                msg, paperId);
        }
    }
}
