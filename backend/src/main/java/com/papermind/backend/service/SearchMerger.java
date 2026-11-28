package com.papermind.backend.service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * #76 双源检索结果合并。
 * 输入：arXiv 返回的列表、OpenAlex 返回的列表；
 * 输出：三级去重后按年份倒序排列、截断到 size 条的列表。
 */
public final class SearchMerger {

    private SearchMerger() {
        // 纯工具类，不需要实例
    }

    public static List<Map<String, Object>> merge(List<Map<String, Object>> primary,
                                                  List<Map<String, Object>> secondary,
                                                  int size) {
        Map<String, Map<String, Object>> index = new HashMap<>();
        List<Map<String, Object>> merged = new ArrayList<>();

        collect(index, merged, primary);
        collect(index, merged, secondary);

        merged.sort(SearchMerger::compare);

        if (merged.size() <= size) {
            return merged;
        }
        return new ArrayList<>(merged.subList(0, size));
    }

    private static void collect(Map<String, Map<String, Object>> index,
                                List<Map<String, Object>> merged,
                                List<Map<String, Object>> items) {
        if (items == null) {
            return;
        }
        for (Map<String, Object> item : items) {
            if (item == null) {
                continue;
            }
            List<String> keys = keysOf(item);

            Map<String, Object> same = null;
            for (String key : keys) {
                same = index.get(key);
                if (same != null) {
                    break;
                }
            }

            if (same == null) {
                merged.add(item);
                for (String key : keys) {
                    index.put(key, item);
                }
            } else {
                combine(same, item);
                for (String key : keys) {
                    index.putIfAbsent(key, same);
                }
            }
        }
    }

    private static List<String> keysOf(Map<String, Object> item) {
        List<String> keys = new ArrayList<>(3);

        String doi = text(item.get("doi"));
        if (doi != null) {
            keys.add("doi:" + doi.toLowerCase());
        }

        String arxivId = text(item.get("arxivId"));
        if (arxivId != null) {
            keys.add("ax:" + arxivId.toLowerCase());
        }

        String title = text(item.get("title"));
        if (title != null) {
            keys.add("ty:" + title.toLowerCase().replaceAll("\\s+", " ").trim()
                + "|" + text(item.get("year")));
        }
        return keys;
    }

    private static void combine(Map<String, Object> keep, Map<String, Object> other) {
        fillBlank(keep, other, "doi");
        fillBlank(keep, other, "arxivId");
        fillBlank(keep, other, "pdfUrl");
        fillBlank(keep, other, "landingUrl");

        keep.put("title", longerText(keep.get("title"), other.get("title")));
        keep.put("abstract", longerText(keep.get("abstract"), other.get("abstract")));

        List<String> mine = authors(keep.get("authors"));
        List<String> theirs = authors(other.get("authors"));
        if (theirs.size() > mine.size()) {
            keep.put("authors", theirs);
        }

        Integer mineYear = intOf(keep.get("year"));
        Integer theirYear = intOf(other.get("year"));
        if (mineYear == null) {
            if (theirYear != null) {
                keep.put("year", theirYear);
            }
        } else if (theirYear != null && theirYear < mineYear) {
            keep.put("year", theirYear);
        }
    }

    private static void fillBlank(Map<String, Object> keep, Map<String, Object> other, String field) {
        if (text(keep.get(field)) != null) {
            return;
        }
        Object value = other.get(field);
        if (text(value) != null) {
            keep.put(field, value);
        }
    }

    private static Object longerText(Object a, Object b) {
        String left = text(a);
        String right = text(b);
        if (left == null) {
            return right;
        }
        if (right == null) {
            return left;
        }
        return right.length() > left.length() ? right : left;
    }

    @SuppressWarnings("unchecked")
    private static List<String> authors(Object value) {
        if (value instanceof List) {
            return (List<String>) value;
        }
        return new ArrayList<>();
    }

    private static int compare(Map<String, Object> a, Map<String, Object> b) {
        Integer yearA = intOf(a.get("year"));
        Integer yearB = intOf(b.get("year"));

        if (yearA == null && yearB != null) {
            return 1;
        }
        if (yearA != null && yearB == null) {
            return -1;
        }
        if (yearA != null && !yearA.equals(yearB)) {
            return Integer.compare(yearB, yearA);
        }

        int byArxiv = compareText(a.get("arxivId"), b.get("arxivId"));
        if (byArxiv != 0) {
            return byArxiv;
        }

        return compareText(a.get("doi"), b.get("doi"));
    }

    private static int compareText(Object a, Object b) {
        String left = text(a);
        String right = text(b);
        if (left == null && right == null) {
            return 0;
        }
        if (left == null) {
            return 1;
        }
        if (right == null) {
            return -1;
        }
        return left.compareToIgnoreCase(right);
    }

    private static String text(Object value) {
        if (value == null) {
            return null;
        }
        String s = String.valueOf(value).trim();
        return s.isEmpty() ? null : s;
    }

    private static Integer intOf(Object value) {
        if (value instanceof Number) {
            return ((Number) value).intValue();
        }
        String s = text(value);
        if (s == null) {
            return null;
        }
        try {
            return Integer.parseInt(s);
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
