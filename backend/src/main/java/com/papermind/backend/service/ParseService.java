package com.papermind.backend.service;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

@Service
public class ParseService {

    private final JdbcTemplate jdbcTemplate;

    public ParseService(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    @Async
    public void parseAsync(Long paperId, String filePath) {
        try {
            jdbcTemplate.update("UPDATE papers SET parse_status = 'parsing' WHERE id = ?", paperId);

            // TODO(P4): 替换为调用 P5 /internal/papers/parse
            Thread.sleep(3000);
            int pageCount = 15;
            int chunkCount = 128;

            jdbcTemplate.update(
                "UPDATE papers SET parse_status = 'ready', page_count = ?, chunk_count = ? WHERE id = ?",
                pageCount, chunkCount, paperId);

        } catch (Exception e) {
            jdbcTemplate.update(
                "UPDATE papers SET parse_status = 'failed', parse_error = ? WHERE id = ?",
                e.getMessage(), paperId);
        }
    }
}
