"""开发工具：完整验证「抽取 → 切片 → 向量化 → 入库」，用于 #18。"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.db.chunks import save_chunks
from app.db.connection import get_connection
from app.services.chunker import build_chunks
from app.services.embedder import embed_texts
from app.services.pdf_extractor import extract_blocks


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = os.path.join(BASE_DIR, "data", "attention.pdf")

    if not os.path.exists(path):
        print("文件不存在:", path)
        sys.exit(1)

    # 1. 抽取 + 切片
    blocks, total_pages = extract_blocks(path)
    chunks = build_chunks(blocks)
    print("页数:", total_pages, "| 块数:", len(blocks), "| 切片:", len(chunks))

    # 2. 造一条 papers 记录（正式流程里由 P4 创建）
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into papers (title, filename, file_path) "
                "values (%s, %s, %s) returning id",
                ("__test__", "attention.pdf", path),
            )
            paper_id = cur.fetchone()[0]
    print("测试 paper_id:", paper_id)

    # 3. 向量化
    texts = []
    for c in chunks:
        texts.append(c["content"])
    start = time.time()
    vectors = embed_texts(texts)
    print("编码耗时(秒):", round(time.time() - start, 1))
    print("向量形状:", vectors.shape)

    # 4. 入库
    count = save_chunks(paper_id, chunks, vectors)
    print("写入切片:", count)

    # 5. 查回验证
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select count(*), min(page), max(page) from chunks where paper_id = %s",
                (paper_id,),
            )
            row = cur.fetchone()
            print("库中: 条数=%s, page=%s..%s" % row)

            cur.execute(
                "select chunk_index, page, char_count, vector_dims(embedding) "
                "from chunks where paper_id = %s order by chunk_index limit 3",
                (paper_id,),
            )
            for r in cur.fetchall():
                print("  chunk_index=%s page=%s 字数=%s 维度=%s" % r)

    # 6. 清理测试数据（级联删除会带走 chunks）
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from papers where id = %s", (paper_id,))
    print("已清理测试论文")


if __name__ == "__main__":
    main()
