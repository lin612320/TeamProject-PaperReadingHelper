package com.papermind.backend.controller;

import com.papermind.backend.common.ApiResponse;
import com.papermind.backend.common.BizException;
import com.papermind.backend.common.ErrorCode;
import com.papermind.backend.service.ParseService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/papers")
public class PaperController {

    @Value("${app.upload-dir}")
    private String uploadDir;

    private final JdbcTemplate jdbcTemplate;
    private final ParseService parseService;

    public PaperController(JdbcTemplate jdbcTemplate, ParseService parseService) {
        this.jdbcTemplate = jdbcTemplate;
        this.parseService = parseService;
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> list(
        @RequestParam(defaultValue = "1") int page,
        @RequestParam(defaultValue = "20") int size) {

        if (page < 1 || size < 1 || size > 100) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }

        List<Map<String, Object>> items = jdbcTemplate.queryForList(
            "SELECT id, title, filename, "
                + "page_count AS \"pageCount\", "
                + "parse_status AS \"parseStatus\", "
                + "source, "
                + "to_char(created_at, 'YYYY-MM-DD\"T\"HH24:MI:SS') AS \"createdAt\" "
                + "FROM papers WHERE user_id = 1 "
                + "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            size, (page - 1) * size);

        Integer total = jdbcTemplate.queryForObject(
            "SELECT count(*) FROM papers WHERE user_id = 1", Integer.class);

        Map<String, Object> data = new HashMap<>();
        data.put("total", total);
        data.put("items", items);
        return ApiResponse.ok(data);
    }

    @GetMapping("/{paperId}")
    public ApiResponse<Map<String, Object>> detail(@PathVariable Long paperId) {

        Map<String, Object> row;
        try {
            row = jdbcTemplate.queryForMap(
                "SELECT id, title, filename, "
                    + "page_count AS \"pageCount\", "
                    + "chunk_count AS \"chunkCount\", "
                    + "parse_status AS \"parseStatus\", "
                    + "parse_error AS \"parseError\", "
                    + "source, doi, "
                    + "arxiv_id AS \"arxivId\", "
                    + "external_url AS \"externalUrl\", "
                    + "file_size_bytes AS \"fileSize\", "
                    + "to_char(created_at, 'YYYY-MM-DD\"T\"HH24:MI:SS') AS \"createdAt\" "
                    + "FROM papers WHERE id = ? AND user_id = 1",
                paperId);
        } catch (EmptyResultDataAccessException e) {
            throw new BizException(ErrorCode.PAPER_NOT_FOUND);
        }

        return ApiResponse.ok(row);
    }

    @PostMapping
    public ApiResponse<Map<String, Object>> upload(@RequestParam("file") MultipartFile file) {

        // 1. 校验
        if (file.isEmpty()) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }

        String contentType = file.getContentType();
        if (contentType == null || !contentType.equals("application/pdf")) {
            throw new BizException(ErrorCode.FILE_NOT_PDF);
        }

        // 2. 存盘
        File dir = new File(uploadDir);
        if (!dir.exists() && !dir.mkdirs()) {
            throw new BizException(ErrorCode.STORAGE_ERROR);
        }

        String savedName = UUID.randomUUID() + ".pdf";
        File target = new File(dir, savedName);
        try {
            file.transferTo(target.getAbsoluteFile());
        } catch (IOException e) {
            throw new BizException(ErrorCode.STORAGE_ERROR);
        }

        // 3. 写数据库
        String originalName = file.getOriginalFilename();
        String title = (originalName != null && originalName.contains("."))
            ? originalName.substring(0, originalName.lastIndexOf('.'))
            : originalName;

        Long newId = jdbcTemplate.queryForObject(
            "INSERT INTO papers (title, filename, file_path, file_size_bytes, parse_status) "
                + "VALUES (?, ?, ?, ?, 'pending') RETURNING id",
            Long.class,
            title, originalName, target.getAbsolutePath(), file.getSize());

        // 4. 触发异步解析（当前为 mock）
        parseService.parseAsync(newId, target.getAbsolutePath());

        // 5. 返回
        Map<String, Object> data = new HashMap<>();
        data.put("id", newId);
        data.put("title", title);
        data.put("filename", originalName);
        data.put("size", file.getSize());
        data.put("path", target.getAbsolutePath());
        data.put("parseStatus", "pending");
        return ApiResponse.ok(data);
    }
}
