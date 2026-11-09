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

            # bbox_mode 需要 P6 先加列；没加列时只校验 bbox_*
            cur.execute(
                "select 1 from information_schema.columns "
                "where table_name = 'chunks' and column_name = 'bbox_mode'"
            )
            has_bbox_mode = cur.fetchone() is not None

            cur.execute(
                "select count(*) from chunks where paper_id = %s and ("
                "bbox_x0 is null or bbox_y0 is null or "
                "bbox_x1 is null or bbox_y1 is null or "
                "bbox_x0 < 0 or bbox_x1 > 1 or bbox_y0 < 0 or bbox_y1 > 1 or "
                "bbox_x0 >= bbox_x1 or bbox_y0 >= bbox_y1)",
                (paper_id,),
            )
            invalid_bbox = cur.fetchone()[0]
            print("bbox 校验:", "PASS" if invalid_bbox == 0 else "FAIL（%d 条非法）" % invalid_bbox)

            columns = (
                "chunk_index, page, char_count, "
                "bbox_x0, bbox_y0, bbox_x1, bbox_y1"
            )
            if has_bbox_mode:
                columns = columns + ", bbox_mode"
            columns = columns + ", vector_dims(embedding)"

            cur.execute(
                "select " + columns + " from chunks "
                "where paper_id = %s order by chunk_index limit 3",
                (paper_id,),
            )
            for r in cur.fetchall():
                if has_bbox_mode:
                    print(
                        "  chunk_index=%s page=%s 字数=%s "
                        "bbox=(%s,%s,%s,%s) mode=%s 维度=%s" % r
                    )
                else:
                    print(
                        "  chunk_index=%s page=%s 字数=%s "
                        "bbox=(%s,%s,%s,%s) 维度=%s" % r
                    )

            if has_bbox_mode:
                cur.execute(
                    "select count(*) from chunks where paper_id = %s and ("
                    "bbox_mode is null or bbox_mode not in ('precise','block'))",
                    (paper_id,),
                )
                invalid_mode = cur.fetchone()[0]
                print(
                    "bbox_mode 校验:",
                    "PASS" if invalid_mode == 0 else "FAIL（%d 条非法）" % invalid_mode,
                )
            else:
                print("bbox_mode: 列不存在（P6 尚未加列，本次只写 bbox_*）")

    # 6. 清理测试数据（级联删除会带走 chunks）
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from papers where id = %s", (paper_id,))
    print("已清理测试论文")


if __name__ == "__main__":
    main()
