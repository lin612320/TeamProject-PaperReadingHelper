package com.papermind.backend.controller;

import com.papermind.backend.common.ApiResponse;
import com.papermind.backend.common.BizException;
import com.papermind.backend.common.ErrorCode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
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
@RequestMapping("/api/explain")
public class ExplainController {

    private static final Logger log = LoggerFactory.getLogger(ExplainController.class);

    private static final int MAX_TEXT = 1000;

    private static final int MAX_CONTEXT = 600;

    @Value("${app.ai-service.url:http://localhost:8000}")
    private String aiServiceUrl;

    @Value("${app.explain.timeout-seconds:25}")
    private long explainTimeoutSeconds;

    @PostMapping
    public ApiResponse<Map<String, Object>> explain(@RequestBody Map<String, Object> body) {

        String text = text(body.get("text"));
        if (text.isEmpty()) {
            throw new BizException(ErrorCode.INVALID_PARAM, "选中文本不能为空");
        }

        int textLength = text.length();
        boolean truncatedByBackend = textLength > MAX_TEXT;
        if (truncatedByBackend) {
            text = text.substring(0, MAX_TEXT);
        }

        String mode = text(body.get("mode"));
        if (mode.isEmpty()) {
            mode = "translate";
        }
        if (!"translate".equals(mode) && !"term".equals(mode)) {
            throw new BizException(ErrorCode.INVALID_PARAM, "mode 只能是 translate 或 term");
        }

        Map<String, Object> req = new HashMap<>();
        req.put("text", text);
        req.put("mode", mode);

        Object paperIdRaw = body.get("paperId");
        if (paperIdRaw != null && !String.valueOf(paperIdRaw).trim().isEmpty()) {
            try {
                req.put("paperId", Long.parseLong(String.valueOf(paperIdRaw).trim()));
            } catch (NumberFormatException e) {
                throw new BizException(ErrorCode.INVALID_PARAM, "paperId 必须是数字");
            }
        }

        String context = text(body.get("context"));
        if (context.length() > MAX_CONTEXT) {
            context = context.substring(0, MAX_CONTEXT);
        }
        if (!context.isEmpty()) {
            req.put("context", context);
        }

        putIfPresent(req, "apiKey", body.get("apiKey"));
        putIfPresent(req, "baseUrl", body.get("baseUrl"));
        putIfPresent(req, "model", body.get("model"));

        Map<?, ?> aiResp = callAiService(req);

        boolean truncated = truncatedByBackend
            || Boolean.TRUE.equals(aiResp.get("truncated"));

        Map<String, Object> data = new HashMap<>();
        data.put("translation", aiResp.get("translation") == null ? "" : aiResp.get("translation"));
        data.put("explanation", aiResp.get("explanation") == null ? "" : aiResp.get("explanation"));
        data.put("mode", aiResp.get("mode") == null ? mode : aiResp.get("mode"));
        data.put("truncated", truncated);

        log.info("explain done textLen={} mode={} truncated={} paperId={}",
            textLength, mode, truncated, req.get("paperId"));

        return ApiResponse.ok(data);
    }

    private Map<?, ?> callAiService(Map<String, Object> req) {
        try {
            String json = new com.fasterxml.jackson.databind.ObjectMapper()
                .writeValueAsString(req);

            HttpClient client = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(3))
                .followRedirects(HttpClient.Redirect.NEVER)
                .build();

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(aiServiceUrl + "/internal/explain"))
                .timeout(Duration.ofSeconds(explainTimeoutSeconds))
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
                log.error("ai explain failed status={} code={}", response.statusCode(), code);
                throw new BizException(mapError(aiResp, response.statusCode()));
            }

            if (aiResp == null) {
                throw new BizException(ErrorCode.AI_SERVICE_ERROR);
            }
            return aiResp;

        } catch (java.net.http.HttpTimeoutException e) {
            log.error("ai explain timeout", e);
            throw new BizException(ErrorCode.AI_SERVICE_TIMEOUT);
        } catch (BizException e) {
            throw e;
        } catch (Exception e) {
            log.error("ai explain error", e);
            throw new BizException(ErrorCode.AI_SERVICE_ERROR);
        }
    }

    private ErrorCode mapError(Map<?, ?> body, int status) {
        Object codeObj = body == null ? null : body.get("code");
        String code = codeObj == null ? "" : String.valueOf(codeObj);

        if ("INVALID_MODE".equals(code) || "EMPTY_TEXT".equals(code)) {
            return ErrorCode.INVALID_PARAM;
        }
        if ("LLM_TIMEOUT".equals(code)) {
            return ErrorCode.AI_SERVICE_TIMEOUT;
        }
        if ("LLM_AUTH_ERROR".equals(code)) {
            return ErrorCode.AI_SERVICE_AUTH_ERROR;
        }
        if (status == 401 || status == 403) {
            return ErrorCode.AI_SERVICE_AUTH_ERROR;
        }
        if (status == 422) {
            return ErrorCode.INVALID_PARAM;
        }
        if (status == 504) {
            return ErrorCode.AI_SERVICE_TIMEOUT;
        }
        return ErrorCode.AI_SERVICE_ERROR;
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

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }
}
