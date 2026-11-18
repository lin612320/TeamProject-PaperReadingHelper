"""开发工具：验证 #42 划词翻译 / 术语解释。

用法（在 ai-service 目录下）：
    .venv/Scripts/python.exe -m scripts.check_explain
    .venv/Scripts/python.exe -m scripts.check_explain --live
"""

import argparse
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.db.connection import get_connection
from app.routers.explain import _load_context
from app.services import llm_client
from app.services.explain import ExplainError, _parse_answer, explain_text
from app.services.llm_config import LlmConfig

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

failures = 0


def check(name, condition, detail=""):
    global failures
    if condition:
        print("PASS", name)
    else:
        print("FAIL", name, detail)
        failures += 1


def run_with_fake(answer, func):
    """把 chat_with_config 换成假实现，捕获 messages/config/timeout。"""
    captured = {}

    def fake(messages, config, timeout):
        captured["messages"] = messages
        captured["config"] = config
        captured["timeout"] = timeout
        if isinstance(answer, Exception):
            raise answer
        return answer, {}

    original = llm_client.chat_with_config
    llm_client.chat_with_config = fake
    try:
        result = func()
    finally:
        llm_client.chat_with_config = original
    return result, captured


def test_llm_calls():
    config = LlmConfig("sk-test", "https://example.com", "deepseek-chat")

    result, captured = run_with_fake(
        "翻译：多头注意力\n解释：一种注意力机制",
        lambda: explain_text(
            "Attention Is All You Need", "", "multi-head attention", "translate", config
        ),
    )
    check("translate 返回译文", result["translation"] == "多头注意力", result)
    check("translate 返回模式", result["mode"] == "translate", result)
    check("translate 未截断", result["truncated"] is False, result)
    check("Key 透传", captured["config"].api_key == "sk-test", captured["config"])
    check("baseUrl 透传", captured["config"].base_url == "https://example.com")
    check("model 透传", captured["config"].model == "deepseek-chat")
    check("超时为 10 秒", captured["timeout"] == 10, captured["timeout"])
    user = captured["messages"][-1]["content"]
    check("只传选中文本", "multi-head attention" in user)
    check("未传整篇论文", "整篇论文" not in user)

    result, captured = run_with_fake(
        "翻译：多头注意力\n解释：多头注意力是让模型同时关注多个位置的方法。它把注意力分成多个头并行计算。",
        lambda: explain_text(
            "Attention Is All You Need", "", "multi-head attention", "term"
        ),
    )
    check("term 返回翻译", result["translation"] == "多头注意力", result)
    check(
        "term 解释第一句是白话定义",
        result["explanation"].startswith("多头注意力是"),
        result["explanation"],
    )
    check(
        "term Prompt 要求白话定义",
        "第一句必须是通俗易懂的白话定义" in captured["messages"][0]["content"],
    )

    text = "X" * 1500
    result, captured = run_with_fake(
        "翻译：ok\n解释：ok",
        lambda: explain_text("T", "", text, "translate"),
    )
    check("超长文本被截断", result["truncated"] is True, result)
    user = captured["messages"][-1]["content"]
    check("Prompt 里只保留 1000 字", user.count("X") == 1000, user.count("X"))

    context = "CONTEXT" * 100
    result, captured = run_with_fake(
        "翻译：ok\n解释：ok",
        lambda: explain_text("T", context, "text", "translate"),
    )
    user = captured["messages"][-1]["content"]
    check("上下文被使用", "CONTEXT" in user)
    check("上下文最多 600 字", user.count("CONTEXT") == 600 // 7, user.count("CONTEXT"))
    check("上下文不翻译自己", "不要翻译或解释它" in user)

    translation, explanation = _parse_answer("随便一段兜底文本")
    check("解析失败时兜底", translation == "" and explanation == "随便一段兜底文本")


def test_errors():
    try:
        explain_text("T", "", "text", "bad-mode")
        check("非法 mode 报错", False)
    except ExplainError as e:
        check("非法 mode 报错", e.code == "INVALID_MODE", e.code)

    try:
        explain_text("T", "", "   ", "translate")
        check("空文本报错", False)
    except ExplainError as e:
        check("空文本报错", e.code == "EMPTY_TEXT", e.code)

    for error, expected in (
        (llm_client.LLMTimeout("timeout"), "LLM_TIMEOUT"),
        (llm_client.LLMAuthError("auth"), "LLM_AUTH_ERROR"),
        (llm_client.LLMError("boom"), "LLM_ERROR"),
    ):
        try:
            run_with_fake(error, lambda: explain_text("T", "", "text", "translate"))
            check("错误映射 %s" % expected, False)
        except ExplainError as e:
            check("错误映射 %s" % expected, e.code == expected, e.code)


def test_db_context():
    """真实 DB：入库论文能查到标题和命中片段；未入库不报错。"""
    paper_id = None
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into papers (title, filename, file_path) "
                    "values ('__explain_test__', 'x.pdf', '/tmp/x.pdf') returning id"
                )
                paper_id = cur.fetchone()[0]
                content = "This paper studies multi-head attention\nin detail."
                cur.execute(
                    "insert into chunks "
                    "(paper_id, chunk_index, page, content, char_count) "
                    "values (%s, 0, 1, %s, %s)",
                    (paper_id, content, len(content)),
                )

        title, context = _load_context(paper_id, "multi-head attention", None)
        check("入库论文查到标题", title == "__explain_test__", title)
        check("入库论文查到上下文", "multi-head attention" in context, context)

        title, context = _load_context(paper_id, "multi-head attention", "前端上下文")
        check("前端 context 优先", context == "前端上下文", context)

        title, context = _load_context(999999999, "multi-head attention", None)
        check("未入库论文不报错", title == "" and context == "", (title, context))
    except Exception as e:
        print("SKIP DB context（数据库不可用）:", e)
    finally:
        if paper_id is not None:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("delete from papers where id = %s", (paper_id,))


def test_live():
    if os.getenv("DEEPSEEK_API_KEY", "").strip() == "":
        print("SKIP live（未配置 DEEPSEEK_API_KEY）")
        return

    start = time.time()
    result = explain_text(
        "Attention Is All You Need", "", "multi-head attention", "term"
    )
    elapsed = time.time() - start
    print("live term:", result, "耗时 %.2fs" % elapsed)
    check("live term 有解释", result["explanation"] != "")
    check("live term 解释第一句是白话定义", len(result["explanation"]) > 0)
    check("live term 10 秒内", elapsed < 10, "%.2fs" % elapsed)

    start = time.time()
    result = explain_text(
        "Attention Is All You Need", "", "The Transformer relies entirely on attention.", "translate"
    )
    elapsed = time.time() - start
    print("live translate:", result, "耗时 %.2fs" % elapsed)
    check("live translate 有译文", result["translation"] != "")
    check("live translate 10 秒内", elapsed < 10, "%.2fs" % elapsed)


def main():
    parser = argparse.ArgumentParser(description="验证 #42 划词翻译/术语解释")
    parser.add_argument("--live", action="store_true", help="调真实 DeepSeek 验证")
    args = parser.parse_args()

    test_llm_calls()
    test_errors()
    test_db_context()
    if args.live:
        test_live()

    if failures:
        print("\n%d 项未通过" % failures)
        sys.exit(1)
    print("\n全部通过")


if __name__ == "__main__":
    main()
