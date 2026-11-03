package com.papermind.backend.controller;

import com.papermind.backend.common.ApiResponse;
import com.papermind.backend.common.BizException;
import com.papermind.backend.common.ErrorCode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/qa")
public class QaController {

    private static final Logger log = LoggerFactory.getLogger(QaController.class);

    private final JdbcTemplate jdbcTemplate;
    private final RestTemplate restTemplate;

    @Value("${app.ai-service.url:http://localhost:8000}")
    private String aiServiceUrl;

    public QaController(JdbcTemplate jdbcTemplate, RestTemplate restTemplate) {
        this.jdbcTemplate = jdbcTemplate;
        this.restTemplate = restTemplate;
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

        // 必须是 ready 才能提问
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

        Map<?, ?> aiResp;
        try {
            ResponseEntity<Map> resp = restTemplate.postForEntity(
                aiServiceUrl + "/internal/qa/ask", req, Map.class);
            aiResp = resp.getBody();
        } catch (ResourceAccessException e) {
            if (e.getCause() instanceof java.net.ConnectException) {
                log.error("ai service unreachable, paperId={}", paperId, e);
                throw new BizException(ErrorCode.AI_SERVICE_ERROR);
            }
            log.error("ai service timeout, paperId={}", paperId, e);
            throw new BizException(ErrorCode.AI_SERVICE_TIMEOUT);
        } catch (RestClientException e) {
            log.error("ai service error, paperId={}", paperId, e);
            throw new BizException(ErrorCode.AI_SERVICE_ERROR);
        }

        if (aiResp == null) {
            throw new BizException(ErrorCode.AI_SERVICE_ERROR);
        }

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
}
