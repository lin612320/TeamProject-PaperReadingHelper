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
            + "&sortBy=relevance&sortOrder=descending";

        log.info("arxiv search keyword={} start={} max={}", keyword, start, maxResults);

        HttpClient client = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)   // 与内部服务一致，避免 HTTP/2 升级带来的问题
            .connectTimeout(Duration.ofSeconds(3))
            .followRedirects(HttpClient.Redirect.NORMAL)   // arXiv 可能 301，要能跟
            .build();

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .timeout(Duration.ofSeconds(timeoutSeconds))
            .header("User-Agent", "PaperMind-Alpha/1.0 (course project)")
            .GET()
            .build();

        HttpResponse<byte[]> response =
            client.send(request, HttpResponse.BodyHandlers.ofByteArray());

        if (response.statusCode() != 200) {
            throw new IllegalStateException("arXiv 返回 HTTP " + response.statusCode());
        }

        return parse(response.body());
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
            String href = link.getAttribute("href");
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
