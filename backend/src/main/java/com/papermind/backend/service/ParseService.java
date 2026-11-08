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

    @Value("${app.parse.force:false}")
    private boolean force;

    @Value("${app.parse.timeout-seconds:180}")
    private long parseTimeoutSeconds;

    @Value("${app.ai-service.url:http://localhost:8000}")
    private String aiServiceUrl;

    public ParseService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Async
    public void parseAsync(Long paperId, String filePath) {
        long startMs = System.currentTimeMillis();
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

                java.net.http.HttpClient client = java.net.http.HttpClient.newBuilder()
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
                    throw new IllegalStateException("AI 服务返回 " + httpResponse.statusCode()
                        + "：" + shorten(httpResponse.body(), 300));
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

            log.info("parse done paperId={} cost={}ms pageCount={} chunkCount={}",
                paperId, System.currentTimeMillis() - startMs, pageCount, chunkCount);

        } catch (java.net.http.HttpConnectTimeoutException e) {
            fail(paperId, "无法连接 AI 服务（" + aiServiceUrl + "）：连接超时，请确认 ai-service 已启动", e);
        } catch (java.net.http.HttpTimeoutException e) {
            fail(paperId, "解析超时：AI 服务未在 " + parseTimeoutSeconds
                + " 秒内返回（文档切片较多或服务繁忙）", e);
        } catch (java.net.ConnectException e) {
            fail(paperId, "无法连接 AI 服务（" + aiServiceUrl + "）：连接被拒绝，请确认 ai-service 已启动", e);
        } catch (Exception e) {
            String detail = (e.getMessage() == null || e.getMessage().isBlank())
                ? e.getClass().getSimpleName()
                : e.getMessage();
            fail(paperId, "解析失败：" + detail, e);
        }
    }

    private void fail(Long paperId, String reason, Exception e) {
        log.error("parse failed, paperId={} reason={}", paperId, reason, e);
        jdbcTemplate.update(
            "UPDATE papers SET parse_status = 'failed', parse_error = ? WHERE id = ?",
            shorten(reason, 500), paperId);
    }

    private String shorten(String s, int max) {
        if (s == null) {
            return "";
        }
        return s.length() <= max ? s : s.substring(0, max);
    }
}
