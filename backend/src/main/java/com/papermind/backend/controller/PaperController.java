package com.papermind.backend.controller;

import com.papermind.backend.common.ApiResponse;
import com.papermind.backend.common.BizException;
import com.papermind.backend.common.ErrorCode;
import com.papermind.backend.service.ParseService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
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
        return ApiResponse.ok(loadDetail(paperId));
    }

    @GetMapping("/{paperId}/file")
    public ResponseEntity<byte[]> file(@PathVariable Long paperId) {

        String filePath;
        try {
            filePath = jdbcTemplate.queryForObject(
                "SELECT file_path FROM papers WHERE id = ? AND user_id = 1",
                String.class, paperId);
        } catch (EmptyResultDataAccessException e) {
            throw new BizException(ErrorCode.PAPER_NOT_FOUND);
        }

        File pdf = new File(filePath);
        if (!pdf.exists()) {
            throw new BizException(ErrorCode.PAPER_NOT_FOUND);
        }

        byte[] bytes;
        try {
            bytes = Files.readAllBytes(pdf.toPath());
        } catch (IOException e) {
            throw new BizException(ErrorCode.STORAGE_ERROR);
        }

        return ResponseEntity.ok()
            .contentType(MediaType.APPLICATION_PDF)
            .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + paperId + ".pdf\"")
            .body(bytes);
    }

    @DeleteMapping("/{paperId}")
    public ApiResponse<Void> delete(@PathVariable Long paperId) {

        String filePath;
        try {
            filePath = jdbcTemplate.queryForObject(
                "SELECT file_path FROM papers WHERE id = ? AND user_id = 1",
                String.class, paperId);
        } catch (EmptyResultDataAccessException e) {
            throw new BizException(ErrorCode.PAPER_NOT_FOUND);
        }

        jdbcTemplate.update("DELETE FROM papers WHERE id = ? AND user_id = 1", paperId);

        if (filePath != null) {
            try {
                Files.deleteIfExists(new File(filePath).toPath());
            } catch (IOException ignored) {
                // 删文件失败不影响数据库删除
            }
        }

        return ApiResponse.ok(null);
    }

    @PostMapping
    public ApiResponse<Map<String, Object>> upload(@RequestParam("file") MultipartFile file) {

        if (file.isEmpty()) {
            throw new BizException(ErrorCode.INVALID_PARAM);
        }

        // 校验一（BUG-009）：后缀必须是 .pdf，与前端的判据保持一致
        String originalName = file.getOriginalFilename();
        if (originalName == null || !originalName.toLowerCase().endsWith(".pdf")) {
            throw new BizException(ErrorCode.FILE_NOT_PDF);
        }

        // 校验二（BUG-004）：内容必须是 PDF——文件头 %PDF
        // 只校验后缀不够：纯文本改名成 .pdf 会被放进来，造成脏数据入库
        if (!isPdf(file)) {
            throw new BizException(ErrorCode.FILE_NOT_PDF);
        }

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

        String title = (originalName.contains("."))
            ? originalName.substring(0, originalName.lastIndexOf('.'))
            : originalName;

        Long newId = jdbcTemplate.queryForObject(
            "INSERT INTO papers (title, filename, file_path, file_size_bytes, parse_status) "
                + "VALUES (?, ?, ?, ?, 'pending') RETURNING id",
            Long.class,
            title, originalName, target.getAbsolutePath(), file.getSize());

        parseService.parseAsync(newId, target.getAbsolutePath());

        // BUG-002 / BUG-003：直接返回契约规定的 PaperDetail，不再暴露 path / size
        return ApiResponse.ok(loadDetail(newId));
    }

    private Map<String, Object> loadDetail(Long paperId) {
        try {
            return jdbcTemplate.queryForMap(
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
    }

    private boolean isPdf(MultipartFile file) {
        try (InputStream in = file.getInputStream()) {
            byte[] head = new byte[5];
            int n = in.read(head);
            return n >= 4
                && head[0] == 0x25   // %
                && head[1] == 0x50   // P
                && head[2] == 0x44   // D
                && head[3] == 0x46;  // F
        } catch (IOException e) {
            return false;
        }
    }
}
