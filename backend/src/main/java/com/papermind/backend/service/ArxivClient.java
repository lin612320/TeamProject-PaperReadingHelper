package com.papermind.backend.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import java.io.ByteArrayInputStream;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;


@Service
public class ArxivClient {

    private static final Logger log = LoggerFactory.getLogger(ArxivClient.class);

    @Value("${app.search.arxiv-url:http://export.arxiv.org/api/query}")
    private String arxivUrl;

    @Value("${app.search.timeout-seconds:10}")
    private long timeoutSeconds;

    public static class Result {
        public int total;
        public List<Map<String, Object>> items = new ArrayList<>();
    }

    /**
     * arXiv 限流（429/403）专用异常。
     *
     * 单独一个类型是为了两件事：
     *   1. 不进入重试——被限流时重试只会把 30 秒预算全耗光，然后还是失败；
     *   2. 上层能据此判断"是源在限流，不是我们的代码坏了"，直接回落 OpenAlex。
     */
    public static class RateLimitedException extends RuntimeException {
        public RateLimitedException(String message) {
            super(message);
        }
    }

    /**
     * @param keyword    关键词（已 trim，调用方保证非空）
     * @param start      偏移量 = (page-1)*size
     * @param maxResults 本页条数（≤50）
     */
    public Result search(String keyword, int start, int maxResults) throws Exception {
        String query = "all:\"" + keyword.replace("\"", " ") + "\"";
        String url = arxivUrl
            + "?search_query=" + URLEncoder.encode(query, StandardCharsets.UTF_8)
            + "&start=" + start
            + "&max_results=" + maxResults
            + "&sortBy=relevance&sortOrder=descending"; //相关度倒序

        log.info("arxiv search keyword={} start={} max={}", keyword, start, maxResults);

        byte[] body = fetchWithRetry(url);
        return parse(body);
    }


    private byte[] fetchWithRetry(String url) throws Exception {
        int attempts = 2;
        // 有 OpenAlex 兜底之后，不必在 arXiv 上死等满预算：
        // 30 秒 ÷ 2 = 15 秒/次，用户在检索页会干等 30 秒还看不到结果。
        // 封顶 8 秒/次 → 最坏 16 秒就交给兜底，观感从"卡死"变成"稍慢"。
        long perAttempt = Math.min(8, Math.max(3, timeoutSeconds / attempts));
        Exception last = null;

        for (int i = 1; i <= attempts; i++) {
            try {
                return fetchOnce(url, perAttempt);
            } catch (java.net.http.HttpTimeoutException e) {
                last = e;
                log.warn("arxiv 请求超时 第{}次（每次{}秒）", i, perAttempt);
            } catch (java.io.IOException e) {
                last = e;
                log.warn("arxiv 连接失败 第{}次：{}", i, e.toString());
            }
            // RateLimitedException 是 RuntimeException，不在这里捕获 —— 限流就该立刻走兜底
        }
        throw last;   // 两次都失败 → 交给上层降级
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
            .GET()
            .build();

        HttpResponse<byte[]> response =
            client.send(request, HttpResponse.BodyHandlers.ofByteArray());

        if (response.statusCode() == 429 || response.statusCode() == 403) {
            // 限流不是"暂时性抖动"，重试没用，直接快速失败交给上层回落
            throw new RateLimitedException("arXiv 限流，HTTP " + response.statusCode());
        }
        if (response.statusCode() != 200) {
            throw new IllegalStateException("arXiv 返回 HTTP " + response.statusCode());
        }
        return response.body();
    }

    private Result parse(byte[] xml) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
        factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);

        DocumentBuilder builder = factory.newDocumentBuilder();
        Document doc = builder.parse(new ByteArrayInputStream(xml));

        Result result = new Result();
        result.total = readTotal(doc);

        NodeList entries = doc.getElementsByTagNameNS("*", "entry");
        for (int i = 0; i < entries.getLength(); i++) {
            Element entry = (Element) entries.item(i);
            result.items.add(toPaperMeta(entry));
        }
        return result;
    }

    /** <opensearch:totalResults> */
    private int readTotal(Document doc) {
        NodeList nodes = doc.getElementsByTagNameNS(
            "http://a9.com/-/spec/opensearch/1.1/", "totalResults");
        if (nodes.getLength() == 0) {
            return 0;
        }
        String text = nodes.item(0).getTextContent();
        try {
            return Integer.parseInt(text.trim());
        } catch (NumberFormatException e) {
            return 0;
        }
    }

    private Map<String, Object> toPaperMeta(Element entry) {
        Map<String, Object> meta = new HashMap<>();

        String arxivId = cleanArxivId(textOf(entry, "id"));
        meta.put("title", collapseWhitespace(textOf(entry, "title")));
        meta.put("authors", readAuthors(entry));
        meta.put("year", readYear(textOf(entry, "published")));
        meta.put("source", "arxiv");
        meta.put("doi", null);
        meta.put("arxivId", arxivId);
        meta.put("abstract", collapseWhitespace(textOf(entry, "summary")));

        String landingUrl = null;
        String pdfUrl = null;
        NodeList links = entry.getElementsByTagNameNS("*", "link");
        for (int i = 0; i < links.getLength(); i++) {
            Element link = (Element) links.item(i);
            String rel = link.getAttribute("rel");
            String title = link.getAttribute("title");
            String href = link.getAttribute("href");  //真实地址
            if (href == null || href.isEmpty()) {
                continue;
            }
            if ("alternate".equals(rel) && landingUrl == null) {
                landingUrl = href;
            }
            if ("pdf".equals(title) && pdfUrl == null) {
                pdfUrl = href;
            }
        }

        meta.put("landingUrl", landingUrl);
        meta.put("pdfUrl", pdfUrl);
        return meta;
    }

    private List<String> readAuthors(Element entry) {
        List<String> authors = new ArrayList<>();
        NodeList names = entry.getElementsByTagNameNS("*", "name");
        for (int i = 0; i < names.getLength(); i++) {
            String name = names.item(i).getTextContent();
            if (name != null && !name.isBlank()) {
                authors.add(name.trim());
            }
        }
        return authors;
    }

    private String textOf(Element parent, String tag) {
        NodeList nodes = parent.getElementsByTagNameNS("*", tag);
        return nodes.getLength() == 0 ? null : nodes.item(0).getTextContent();
    }

    private String cleanArxivId(String rawId) {
        if (rawId == null || rawId.isBlank()) {
            return null;
        }
        String id = rawId.trim();
        int slash = id.lastIndexOf('/');
        if (slash >= 0) {
            id = id.substring(slash + 1);
        }
        return id.replaceAll("v\\d+$", "");
    }

    private Integer readYear(String published) {
        if (published == null || published.length() < 4) {
            return null;
        }
        try {
            return Integer.parseInt(published.substring(0, 4));
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private String collapseWhitespace(String s) {
        if (s == null) {
            return null;
        }
        return s.replaceAll("\\s+", " ").trim();
    }
}
