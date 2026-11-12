package com.papermind.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.*;

@Service
public class OpenAlexClient {

    private static final Logger log = LoggerFactory.getLogger(OpenAlexClient.class);

    @Value("${app.search.openalex-url:https://api.openalex.org/works}")
    private String openAlexUrl;

    @Value("${app.search.timeout-seconds:10}")
    private long timeoutSeconds;

    public static class Result {
        public int total;
        public List<Map<String, Object>> items = new ArrayList<>();
    }

    public Result search(String keyword, int page, int size) throws Exception {
        String url = openAlexUrl
            + "?search=" + URLEncoder.encode(keyword, StandardCharsets.UTF_8)
            + "&page=" + page
            + "&per-page=" + size
            + "&mailto=530944058@qq.com";
        log.info("openalex search keyword={} page={} size={}", keyword, page, size);
        return parse(fetchWithRetry(url));
    }

    private byte[] fetchWithRetry(String url) throws Exception {
        int attempts = 2;
        long perAttempt = Math.max(3, timeoutSeconds / attempts);
        Exception last = null;
        for (int i = 1; i <= attempts; i++) {
            try {
                return fetchOnce(url, perAttempt);
            } catch (java.net.http.HttpTimeoutException e) {
                last = e; log.warn("openalex 请求超时 第{}次", i);
            } catch (java.io.IOException e) {
                last = e; log.warn("openalex 连接失败 第{}次：{}", i, e.toString());
            }
        }
        throw last;
    }

    private byte[] fetchOnce(String url, long timeoutSec) throws Exception {
        HttpClient client = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(Duration.ofSeconds(Math.min(3, timeoutSec)))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build();
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .timeout(Duration.ofSeconds(timeoutSec))
            .header("User-Agent", "PaperMind-Alpha/1.0 (course project)")
            .GET().build();
        HttpResponse<byte[]> response =
            client.send(request, HttpResponse.BodyHandlers.ofByteArray());
        if (response.statusCode() != 200) {
            throw new IllegalStateException("OpenAlex 返回 HTTP " + response.statusCode());
        }
        return response.body();
    }

    @SuppressWarnings("unchecked")
    private Result parse(byte[] json) throws Exception {
        Map<String, Object> root = new ObjectMapper().readValue(json, Map.class);
        Result result = new Result();
        Map<String, Object> meta = (Map<String, Object>) root.get("meta");
        if (meta != null && meta.get("count") instanceof Number) {
            result.total = ((Number) meta.get("count")).intValue();
        }
        List<Map<String, Object>> results = (List<Map<String, Object>>) root.get("results");
        if (results != null) {
            for (Map<String, Object> work : results) {
                result.items.add(toPaperMeta(work));
            }
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> toPaperMeta(Map<String, Object> work) {
        Map<String, Object> meta = new HashMap<>();
        meta.put("title", collapse(work.get("display_name")));
        meta.put("authors", readAuthors(work));
        meta.put("year", work.get("publication_year"));
        meta.put("source", "openalex");
        meta.put("doi", stripDoi(work.get("doi")));
        meta.put("arxivId", null);
        meta.put("abstract", rebuildAbstract(
            (Map<String, Object>) work.get("abstract_inverted_index")));

        String pdfUrl = null;
        Map<String, Object> oa = (Map<String, Object>) work.get("open_access");
        if (oa != null && Boolean.TRUE.equals(oa.get("is_oa"))) {
            Map<String, Object> best = (Map<String, Object>) work.get("best_oa_location");
            if (best != null && best.get("pdf_url") != null) {
                pdfUrl = String.valueOf(best.get("pdf_url"));
            } else if (oa.get("oa_url") != null) {
                pdfUrl = String.valueOf(oa.get("oa_url"));
            }
        }
        meta.put("pdfUrl", pdfUrl);

        String landingUrl = null;
        Map<String, Object> primary = (Map<String, Object>) work.get("primary_location");
        if (primary != null && primary.get("landing_page_url") != null) {
            landingUrl = String.valueOf(primary.get("landing_page_url"));
        }
        meta.put("landingUrl", landingUrl);
        return meta;
    }

    @SuppressWarnings("unchecked")
    private List<String> readAuthors(Map<String, Object> work) {
        List<String> authors = new ArrayList<>();
        List<Map<String, Object>> ships = (List<Map<String, Object>>) work.get("authorships");
        if (ships == null) return authors;
        for (Map<String, Object> ship : ships) {
            Map<String, Object> author = (Map<String, Object>) ship.get("author");
            if (author != null && author.get("display_name") != null) {
                authors.add(String.valueOf(author.get("display_name")));
            }
        }
        return authors;
    }

    @SuppressWarnings("unchecked")
    private String rebuildAbstract(Map<String, Object> inverted) {
        if (inverted == null || inverted.isEmpty()) return null;
        TreeMap<Integer, String> ordered = new TreeMap<>();
        for (Map.Entry<String, Object> e : inverted.entrySet()) {
            for (Number pos : (List<Number>) e.getValue()) {
                ordered.put(pos.intValue(), e.getKey());
            }
        }
        return String.join(" ", ordered.values());
    }

    private String stripDoi(Object doi) {
        if (doi == null) return null;
        return String.valueOf(doi).trim()
            .replaceFirst("^https?://(dx\\.)?doi\\.org/", "");
    }

    private String collapse(Object v) {
        if (v == null) return null;
        return String.valueOf(v).replaceAll("\\s+", " ").trim();
    }
}
