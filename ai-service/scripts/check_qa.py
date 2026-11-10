"""开发工具：通过 HTTP 验证 #19 问答接口（qa.py 路由与契约分支）。

需要先启动服务：
    .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
"""

import json
import os
import sys
import urllib.error
import urllib.request

# Windows 控制台按 GBK 输出时，模型答案中的符号会让 print 抛 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.db.connection import get_connection

BASE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_PDF = os.path.join(BASE_DIR, "data", "attention.pdf")


def call(method, path, body=None, timeout=120):
    """发一个 HTTP 请求，返回 (状态码, JSON 响应)。"""
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw}
    except urllib.error.URLError as e:
        print("无法连接 ai-service (%s): %s" % (BASE_URL, e.reason))
        print("请先启动服务: .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000")
        sys.exit(1)


def add_paper(title, file_path):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into papers (title, filename, file_path) "
                "values (%s, %s, %s) returning id",
                (title, os.path.basename(file_path), file_path),
            )
            return cur.fetchone()[0]


def delete_papers(paper_ids):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from papers where id = any(%s)", (list(paper_ids),))


def check(name, got, expected):
    ok = got == expected
    print("%s %s（期望 %s，实际 %s）" % ("PASS" if ok else "FAIL", name, expected, got))
    return ok


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PDF
    if not os.path.exists(path):
        print("文件不存在:", path)
        sys.exit(1)

    status, health = call("GET", "/internal/health", timeout=10)
    if status != 200 or not health.get("dbReady"):
        print("服务未就绪:", status, health)
        sys.exit(1)
    print("服务就绪: status=%s dbReady=%s\n" % (health.get("status"), health.get("dbReady")))

    parsed_id = None
    empty_id = None
    failures = 0
    try:
        parsed_id = add_paper("__qa_route_test__", path)
        empty_id = add_paper("__qa_route_test_empty__", path)

        # 造数据：调解析接口生成 chunks
        status, body = call(
            "POST",
            "/internal/papers/parse",
            {"paperId": parsed_id, "filePath": path},
            timeout=300,
        )
        if status != 200:
            print("解析失败，无法继续:", status, body)
            sys.exit(1)
        print("已解析入库: %s 片\n" % body.get("chunkCount"))

        # 200：正常问答
        if os.getenv("DEEPSEEK_API_KEY", "") == "":
            print("SKIP 正常问答（未配置 DEEPSEEK_API_KEY）\n")
        else:
            status, body = call(
                "POST",
                "/internal/qa/ask",
                {"paperId": parsed_id, "question": "这篇文章提出的方法核心是什么？"},
                timeout=40,
            )
            failures += not check("正常问答 → 200", status, 200)
            if status == 200:
                required = ["answer", "citations", "elapsedMs", "model", "tokenUsage"]
                missing = [key for key in required if key not in body]
                failures += not check("响应字段完整", missing, [])
                failures += not check("citations 是数组", isinstance(body.get("citations"), list), True)
                citations = body.get("citations", [])
                failures += not check(
                    "引用页码从 1 开始",
                    all(item.get("page", 0) >= 1 for item in citations),
                    True,
                )

                bbox_ok = True
                mode_ok = True
                for item in citations:
                    bbox = [
                        item.get("bboxX0"),
                        item.get("bboxY0"),
                        item.get("bboxX1"),
                        item.get("bboxY1"),
                    ]
                    if any(value is None for value in bbox):
                        bbox_ok = False
                        continue
                    if not all(isinstance(value, (int, float)) for value in bbox):
                        bbox_ok = False
                        continue
                    x0, y0, x1, y1 = bbox
                    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
                        bbox_ok = False
                    if item.get("bboxMode") not in ("precise", "block"):
                        mode_ok = False

                failures += not check("citation bbox 有效（0~1、宽高为正）", bbox_ok, True)
                failures += not check("citation bboxMode 有效", mode_ok, True)
                print("答案:", str(body.get("answer", ""))[:80])
            print()

        # 422：空问题
        status, body = call("POST", "/internal/qa/ask", {"paperId": parsed_id, "question": "   "})
        failures += not check("空问题 → 422", status, 422)
        failures += not check("错误码 EMPTY_QUESTION", body.get("code"), "EMPTY_QUESTION")

        # 404：论文不存在
        status, body = call("POST", "/internal/qa/ask", {"paperId": 999999999, "question": "测试"})
        failures += not check("论文不存在 → 404", status, 404)
        failures += not check("错误码 PAPER_NOT_FOUND", body.get("code"), "PAPER_NOT_FOUND")

        # 409：论文存在但还没有 chunks
        status, body = call("POST", "/internal/qa/ask", {"paperId": empty_id, "question": "测试"})
        failures += not check("尚未解析 → 409", status, 409)
        failures += not check("错误码 PAPER_NOT_READY", body.get("code"), "PAPER_NOT_READY")
    finally:
        ids = [paper_id for paper_id in (parsed_id, empty_id) if paper_id is not None]
        if ids:
            delete_papers(ids)
            print("\n已清理测试论文:", ids)

    if failures:
        print("\n%d 项未通过" % failures)
        sys.exit(1)
    print("\n全部通过")


if __name__ == "__main__":
    main()
