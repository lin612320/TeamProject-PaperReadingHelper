package com.papermind.backend.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class ParseService {

    private static final Logger log = LoggerFactory.getLogger(ParseService.class);

    private final JdbcTemplate jdbcTemplate;

    @Value("${app.parse.mock:true}")
    private boolean mock;

    /** 是否强制重建已有切片（契约 force 字段），默认 false */
    @Value("${app.parse.force:false}")
    private boolean force;

    /** 解析接口超时（秒）。P5 首次要加载模型 + 逐段 embedding，25 秒不够 */
    @Value("${app.parse.timeout-seconds:180}")
    private long parseTimeoutSeconds;

    @Value("${app.ai-service.url:http://localhost:8000}")
    private String aiServiceUrl;

    public ParseService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Async
    public void parseAsync(Long paperId, String filePath) {
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

                String json = new com.fasterxml.jackson.databind.ObjectMapper()
                    .writeValueAsString(req);

                java.net.http.HttpClient client = java.net.http.HttpClient.newBuilder()      // AI 服务（uvicorn）不支持 h2c 升级，必须强制 HTTP/1.1，否则请求体会丢失
                    .version(java.net.http.HttpClient.Version.HTTP_1_1)
                    .connectTimeout(java.time.Duration.ofSeconds(3))
                    .followRedirects(java.net.http.HttpClient.Redirect.NEVER)
                    .build();

                java.net.http.HttpRequest httpRequest = java.net.http.HttpRequest.newBuilder()
                    .uri(java.net.URI.create(aiServiceUrl + "/internal/papers/parse"))
                    .timeout(java.time.Duration.ofSeconds(parseTimeoutSeconds))
                    .header("Content-Type", "application/json; charset=utf-8")
                    .POST(java.net.http.HttpRequest.BodyPublishers.ofString(
                        json, java.nio.charset.StandardCharsets.UTF_8))
                    .build();

                java.net.http.HttpResponse<String> httpResponse =
                    client.send(httpRequest, java.net.http.HttpResponse.BodyHandlers.ofString());

                if (httpResponse.statusCode() != 200) {
                    throw new IllegalStateException("AI 服务返回 "
                        + httpResponse.statusCode() + ": " + httpResponse.body());
                }

                Map<?, ?> body = new com.fasterxml.jackson.databind.ObjectMapper()
                    .readValue(httpResponse.body(), Map.class);

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
