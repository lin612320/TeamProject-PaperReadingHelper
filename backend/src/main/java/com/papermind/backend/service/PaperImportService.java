package com.papermind.backend.service;

import com.papermind.backend.common.BizException;
import com.papermind.backend.common.ErrorCode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.io.File;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Map;
import java.util.UUID;

/**
 * 检索结果导入（契约 1.1.0 的 POST /api/papers/import）。
 * 职责：拿到 PaperMeta → 下载 OA 全文 → 建 papers 记录 → 触发异步解析 → 返回 paperId。
 */
@Service
public class PaperImportService {

    private static final Logger log = LoggerFactory.getLogger(PaperImportService.class);

    private final JdbcTemplate jdbcTemplate;
    private final ParseService parseService;

    @Value("${app.upload-dir}")
    private String uploadDir;

    @Value("${app.import.timeout-seconds:60}")
    private long importTimeoutSeconds;

    public PaperImportService(JdbcTemplate jdbcTemplate, ParseService parseService) {
        this.jdbcTemplate = jdbcTemplate;
        this.parseService = parseService;
    }

    /**
     * @param meta 前端把 /api/search 返回的 PaperMeta 原样回传
     * @return 新（或已存在的）paperId
     */
    public long importFromMeta(Map<String, Object> meta) {
        String title = text(meta.get("title"));
        String arxivId = normalizeArxivId(text(meta.get("arxivId")));
        String doi = text(meta.get("doi"));
        String landingUrl = text(meta.get("landingUrl"));
        String pdfUrl = text(meta.get("pdfUrl"));

        if (title.isEmpty()) {
            throw new BizException(ErrorCode.INVALID_PARAM, "缺少 title，无法导入");
        }
        if (arxivId.isEmpty() && doi.isEmpty() && pdfUrl.isEmpty()) {
            throw new BizException(ErrorCode.INVALID_PARAM, "缺少 arxivId / doi / pdfUrl，无法定位全文");
        }

        if (!arxivId.isEmpty()) {
            Long existing = findExistingByArxivId(arxivId);
            if (existing != null) {
                log.info("import skipped, already exists arxivId={} paperId={}", arxivId, existing);
                return existing;
            }
            pdfUrl = "https://arxiv.org/pdf/" + arxivId;
            if (landingUrl.isEmpty()) {
                landingUrl = "https://arxiv.org/abs/" + arxivId;
            }
        }

        if (pdfUrl.isEmpty()) {
            throw new BizException(ErrorCode.AI_SERVICE_ERROR,
                "该论文非开放获取，仅提供原文链接：" + (landingUrl.isEmpty() ? "无" : landingUrl));
        }

        byte[] pdf = download(pdfUrl);
        if (pdf == null || pdf.length < 4
            || pdf[0] != 0x25 || pdf[1] != 0x50 || pdf[2] != 0x44 || pdf[3] != 0x46) {
            throw new BizException(ErrorCode.AI_SERVICE_ERROR,
                "全文下载失败或不是 PDF：" + pdfUrl);
        }

        File dir = new File(uploadDir).getAbsoluteFile();
        if (!dir.exists() && !dir.mkdirs()) {
            throw new BizException(ErrorCode.STORAGE_ERROR);
        }
        String savedName = UUID.randomUUID() + ".pdf";
        File target = new File(dir, savedName);
        try {
            Files.write(target.toPath(), pdf);
        } catch (Exception e) {
            log.error("import save failed path={}", target, e);
            throw new BizException(ErrorCode.STORAGE_ERROR);
        }

        String filename = (arxivId.isEmpty() ? "imported" : arxivId) + ".pdf";
        Long newId = jdbcTemplate.queryForObject(
            "INSERT INTO papers "
                + "(title, filename, file_path, file_size_bytes, parse_status, source, arxiv_id, external_url, doi) "
                + "VALUES (?, ?, ?, ?, 'pending', 'arxiv', ?, ?, ?) RETURNING id",
            Long.class,
            title, filename, savedName, pdf.length,
            arxivId.isEmpty() ? null : arxivId,
            landingUrl.isEmpty() ? null : landingUrl,
            doi.isEmpty() ? null : doi);

        log.info("import ok arxivId={} paperId={} size={}", arxivId, newId, pdf.length);

        parseService.parseAsync(newId, target.getAbsolutePath());
        return newId;
    }

    private Long findExistingByArxivId(String arxivId) {
        try {
            return jdbcTemplate.queryForObject(
                "SELECT id FROM papers WHERE arxiv_id = ? AND user_id = 1 ORDER BY id DESC LIMIT 1",
                Long.class, arxivId);
        } catch (EmptyResultDataAccessException e) {
            return null;
        }
    }

    private byte[] download(String url) {
        try {
            HttpClient client = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(5))
                .followRedirects(HttpClient.Redirect.NORMAL)
                .build();

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofSeconds(importTimeoutSeconds))
                .header("User-Agent", "PaperMind-Alpha/1.0 (course project)")
                .GET()
                .build();

            HttpResponse<byte[]> response =
                client.send(request, HttpResponse.BodyHandlers.ofByteArray());

            if (response.statusCode() != 200) {
                log.warn("import download status={} url={}", response.statusCode(), url);
                return null;
            }
            return response.body();
        } catch (Exception e) {
            log.warn("import download failed url={} err={}", url, e.toString());
            return null;
        }
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String normalizeArxivId(String raw) {
        if (raw.isEmpty()) {
            return "";
        }
        String id = raw;
        int slash = id.lastIndexOf('/');
        if (slash >= 0) {
            id = id.substring(slash + 1);
        }
        return id.replaceAll("v\\d+$", "");
    }
}
