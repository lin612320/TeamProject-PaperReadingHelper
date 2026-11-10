"""开发工具：验证 #19 问答链路（检索 → Prompt → 模型 → 答案 + 引用）。

#40 起同时断言 citations 的 bbox/bboxMode。
用法（在 ai-service 目录下）：
    .venv/Scripts/python.exe -m scripts.check_rag
    .venv/Scripts/python.exe -m scripts.check_rag data/attention.pdf --expect-mode precise
    .venv/Scripts/python.exe -m scripts.check_rag data/baseline/adaptive-rag/adaptive-rag.pdf --expect-mode block
"""

import argparse
import json
import os
import sys

# Windows 控制台按 GBK 输出时，模型答案中的 ∗ 等符号会让 print 抛 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.db.connection import get_connection
from app.services import llm_client
from app.services.ingest import ingest_paper
from app.services.RAG import answer_question


def mock_chat(messages, timeout=20, api_key=None, base_url=None, model=None):
    """没有 API Key 时用的假模型，只验证链路和两种分支。"""
    user = messages[-1]["content"]
    if "量子计算" in user:
        answer = "本文未涉及该内容"
    else:
        answer = "本文提出的核心方法是 Transformer，完全基于注意力机制。"
    usage = {"prompt_tokens": 1200, "completion_tokens": 40, "total_tokens": 1240}
    return answer, usage


def check_bbox_mode_column():
    """检查 chunks.bbox_mode 是否已加列，避免问答时报 UndefinedColumn。"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select 1 from information_schema.columns "
                "where table_name = 'chunks' and column_name = 'bbox_mode'"
            )
            return cur.fetchone() is not None


def _same_number(left, right):
    if left is None or right is None:
        return left is None and right is None
    return abs(float(left) - float(right)) <= 1e-9


def check_citation_db(citation):
    """F6-03：citation 的 bbox/bboxMode 必须与 chunks 表原值一致。"""
    chunk_id = citation.get("chunkId")
    if chunk_id is None:
        print("  FAIL citation: 缺 chunkId，无法对账")
        return 1

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select page, bbox_x0, bbox_y0, bbox_x1, bbox_y1, bbox_mode "
                "from chunks where id = %s",
                (chunk_id,),
            )
            row = cur.fetchone()

    if row is None:
        print("  FAIL citation chunkId=%s: 库中不存在" % chunk_id)
        return 1

    db_page, db_x0, db_y0, db_x1, db_y1, db_mode = row
    same = (
        db_page == citation.get("page")
        and _same_number(db_x0, citation.get("bboxX0"))
        and _same_number(db_y0, citation.get("bboxY0"))
        and _same_number(db_x1, citation.get("bboxX1"))
        and _same_number(db_y1, citation.get("bboxY1"))
        and db_mode == citation.get("bboxMode")
    )
    if not same:
        print(
            "  FAIL citation chunkId=%s: 库=(%s,%s,%s,%s,%s,%s) 接口=(%s,%s,%s,%s,%s,%s)"
            % (
                chunk_id, db_page, db_x0, db_y0, db_x1, db_y1, db_mode,
                citation.get("page"), citation.get("bboxX0"), citation.get("bboxY0"),
                citation.get("bboxX1"), citation.get("bboxY1"), citation.get("bboxMode"),
            )
        )
        return 1
    return 0


def check_citations(result, expect_mode):
    """断言 citations 的 bbox 边界与 bboxMode；返回失败项数量。"""
    citations = result.get("citations", [])
    if not citations:
        print("  citations 为空，跳过 bbox 断言")
        return 0

    failures = 0
    modes = {}
    for i, citation in enumerate(citations):
        bbox = [
            citation.get("bboxX0"),
            citation.get("bboxY0"),
            citation.get("bboxX1"),
            citation.get("bboxY1"),
        ]
        mode = citation.get("bboxMode")
        modes[mode] = modes.get(mode, 0) + 1

        failures += check_citation_db(citation)

        if any(value is None for value in bbox):
            print("  FAIL citation %d: bbox 为 null" % i)
            failures += 1
            continue
        if not all(isinstance(value, (int, float)) for value in bbox):
            print("  FAIL citation %d: bbox 不是 number" % i)
            failures += 1
            continue

        x0, y0, x1, y1 = bbox
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            print("  FAIL citation %d: bbox 越界或宽高非正 %s" % (i, bbox))
            failures += 1
            continue

        if mode not in ("precise", "block"):
            print("  FAIL citation %d: bboxMode 非法 %r" % (i, mode))
            failures += 1
            continue

        if expect_mode is not None and mode != expect_mode:
            print(
                "  FAIL citation %d: bboxMode 期望 %s，实际 %s"
                % (i, expect_mode, mode)
            )
            failures += 1
            continue

        print(
            "  citation %d: page=%s bbox=(%.3f, %.3f, %.3f, %.3f) mode=%s"
            % (i, citation.get("page"), x0, y0, x1, y1, mode)
        )

    print("  bboxMode 分布:", modes)
    return failures


def main():
    parser = argparse.ArgumentParser(description="验证问答链路与 #40 引用 bbox")
    parser.add_argument(
        "path",
        nargs="?",
        default=os.path.join(BASE_DIR, "data", "attention.pdf"),
        help="PDF 路径，默认 data/attention.pdf",
    )
    parser.add_argument(
        "--expect-mode",
        choices=["precise", "block"],
        default=None,
        help="期望的 bboxMode（单栏 precise / 双栏 block）",
    )
    args = parser.parse_args()
    path = args.path

    if not os.path.exists(path):
        print("文件不存在:", path)
        sys.exit(1)

    if not check_bbox_mode_column():
        print("chunks.bbox_mode 列不存在，请先执行：")
        print("  ALTER TABLE chunks ADD COLUMN IF NOT EXISTS bbox_mode TEXT;")
        sys.exit(1)

    # 1. 造一条 papers 记录并解析入库
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into papers (title, filename, file_path) "
                "values (%s, %s, %s) returning id",
                ("__qa_test__", "attention.pdf", path),
            )
            paper_id = cur.fetchone()[0]
    print("测试 paper_id:", paper_id)

    failures = 0
    try:
        stats = ingest_paper(paper_id, path)
        print("入库:", stats["chunkCount"], "片")

        # 2. 没有 Key 就用 mock，保证链路可本地验证
        if os.getenv("DEEPSEEK_API_KEY", "") == "":
            print("未配置 DEEPSEEK_API_KEY，使用 mock 模型验证链路\n")
            llm_client.chat = mock_chat

        questions = [
            "这篇文章提出的方法核心是什么？",
            "本文是否讨论了量子计算在 NLP 中的应用？",
        ]
        for question in questions:
            print("问:", question)
            result = answer_question(paper_id, question, top_k=3, max_citations=3)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            failures += check_citations(result, args.expect_mode)
            print()
    finally:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("delete from papers where id = %s", (paper_id,))
        print("已清理测试论文")

    if failures:
        print("\n%d 项未通过" % failures)
        sys.exit(1)
    print("\nbbox/bboxMode 断言全部通过")


if __name__ == "__main__":
    main()
