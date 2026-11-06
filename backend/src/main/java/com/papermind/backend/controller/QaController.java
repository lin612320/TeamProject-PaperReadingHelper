package com.papermind.backend.controller;

import com.papermind.backend.common.ApiResponse;
import com.papermind.backend.common.BizException;
import com.papermind.backend.common.ErrorCode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/qa")
public class QaController {

    private static final Logger log = LoggerFactory.getLogger(QaController.class);

    private final JdbcTemplate jdbcTemplate;

    @Value("${app.ai-service.url:http://localhost:8000}")
    private String aiServiceUrl;

    public QaController(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @PostMapping("/ask")
    public ApiResponse<Map<String, Object>> ask(@RequestBody Map<String, Object> body) {

        Object paperIdRaw = body.get("paperId");
        Object questionRaw = body.get("question");

        if (paperIdRaw == null || questionRaw == null) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }

        long paperId;
        try {
            paperId = Long.parseLong(String.valueOf(paperIdRaw));
        } catch (NumberFormatException e) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }

        String question = String.valueOf(questionRaw).trim();
        if (question.isEmpty()) {
            throw new BizException(ErrorCode.EMPTY_QUESTION);
        }
        if (question.length() > 500) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }

        String status;
        try {
            status = jdbcTemplate.queryForObject(
                "SELECT parse_status FROM papers WHERE id = ? AND user_id = 1",
                String.class, paperId);
        } catch (EmptyResultDataAccessException e) {
            throw new BizException(ErrorCode.PAPER_NOT_FOUND);
        }

        if (!"ready".equals(status)) {
            throw new BizException(ErrorCode.PAPER_NOT_READY);
        }

        Map<String, Object> req = new HashMap<>();
        req.put("paperId", paperId);
        req.put("question", question);
        req.put("topK", 3);
        req.put("maxCitations", 3);

        putIfPresent(req, "apiKey", body.get("apiKey"));
        putIfPresent(req, "baseUrl", body.get("baseUrl"));
        putIfPresent(req, "model", body.get("model"));

        Map<?, ?> aiResp = callAiService(req, paperId);

        Object tokenUsage = aiResp.get("tokenUsage");
        if (tokenUsage != null) {
            log.info("qa tokenUsage paperId={} usage={}", paperId, tokenUsage);
        }

        Map<String, Object> data = new HashMap<>();
        data.put("answer", aiResp.get("answer"));
        data.put("citations", aiResp.get("citations"));
        data.put("elapsedMs", aiResp.get("elapsedMs"));
        data.put("model", aiResp.get("model"));
        return ApiResponse.ok(data);
    }

    private void putIfPresent(Map<String, Object> req, String key, Object value) {
        if (value == null) {
            return;
        }
        String s = String.valueOf(value).trim();
        if (!s.isEmpty()) {
            req.put(key, s);
        }
    }

    private Map<?, ?> callAiService(Map<String, Object> req, long paperId) {
        try {
            String json = new com.fasterxml.jackson.databind.ObjectMapper()
                .writeValueAsString(req);

            HttpClient client = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(3))
                .followRedirects(HttpClient.Redirect.NEVER)
                .build();

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(aiServiceUrl + "/internal/qa/ask"))
                .timeout(Duration.ofSeconds(25))
                .header("Content-Type", "application/json; charset=utf-8")
                .POST(HttpRequest.BodyPublishers.ofString(json, StandardCharsets.UTF_8))
                .build();

            HttpResponse<String> response = client.send(
                request, HttpResponse.BodyHandlers.ofString());

            Map<?, ?> aiResp = null;
            try {
                aiResp = new com.fasterxml.jackson.databind.ObjectMapper()
                    .readValue(response.body(), Map.class);
            } catch (Exception ignored) {
            }

            if (response.statusCode() != 200) {
                Object code = aiResp == null ? null : aiResp.get("code");
                log.error("ai qa failed, paperId={} status={} code={}",
                    paperId, response.statusCode(), code);
                throw new BizException(mapError(aiResp, response.statusCode()));
            }

            if (aiResp == null) {
                throw new BizException(ErrorCode.AI_SERVICE_ERROR);
            }
            return aiResp;

        } catch (java.net.http.HttpTimeoutException e) {
            log.error("ai qa timeout, paperId={}", paperId, e);
            throw new BizException(ErrorCode.AI_SERVICE_TIMEOUT);
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            log.error("ai qa error, paperId={}", paperId, e);
            throw new BizException(ErrorCode.AI_SERVICE_ERROR);
        }
    }

    private ErrorCode mapError(Map<?, ?> body, int status) {
        Object codeObj = body == null ? null : body.get("code");
        String code = codeObj == null ? "" : String.valueOf(codeObj);

        if ("PAPER_NOT_FOUND".equals(code)) {
            return ErrorCode.PAPER_NOT_FOUND;
        }
        if ("PAPER_NOT_READY".equals(code)) {
            return ErrorCode.PAPER_NOT_READY;
        }
        if ("EMPTY_QUESTION".equals(code)) {
            return ErrorCode.EMPTY_QUESTION;
        }
        if ("LLM_TIMEOUT".equals(code)) {
            return ErrorCode.AI_SERVICE_TIMEOUT;
        }

        if (status == 401) return ErrorCode.AI_SERVICE_ERROR;
        if (status == 404) return ErrorCode.PAPER_NOT_FOUND;
        if (status == 409) return ErrorCode.PAPER_NOT_READY;
        if (status == 422) return ErrorCode.EMPTY_QUESTION;
        if (status == 504) return ErrorCode.AI_SERVICE_TIMEOUT;
        return ErrorCode.AI_SERVICE_ERROR;
    }
}
