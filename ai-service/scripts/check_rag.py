"""开发工具：验证 #19 问答链路（检索 → Prompt → 模型 → 答案 + 引用）。"""

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


def mock_chat(messages, timeout=20):
    """没有 API Key 时用的假模型，只验证链路和两种分支。"""
    user = messages[-1]["content"]
    if "量子计算" in user:
        answer = "本文未涉及该内容"
    else:
        answer = "本文提出的核心方法是 Transformer，完全基于注意力机制。"
    usage = {"prompt_tokens": 1200, "completion_tokens": 40, "total_tokens": 1240}
    return answer, usage


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = os.path.join(BASE_DIR, "data", "attention.pdf")

    if not os.path.exists(path):
        print("文件不存在:", path)
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
            print()
    finally:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("delete from papers where id = %s", (paper_id,))
        print("已清理测试论文")


if __name__ == "__main__":
    main()
