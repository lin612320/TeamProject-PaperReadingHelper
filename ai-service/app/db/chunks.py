"""chunks表的写入"""

import logging

from app.db.connection import get_connection

logger = logging.getLogger(__name__)

INSERT_WITH_MODE = (
    "insert into chunks "
    "(paper_id, chunk_index, page, content, char_count, "
    "bbox_x0, bbox_y0, bbox_x1, bbox_y1, bbox_mode, embedding) "
    "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)"
)

INSERT_WITHOUT_MODE = (
    "insert into chunks "
    "(paper_id, chunk_index, page, content, char_count, "
    "bbox_x0, bbox_y0, bbox_x1, bbox_y1, embedding) "
    "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector)"
)


def vector_to_string(vector):
    """把 1024 个浮点数转成 PostgreSQL 能识别的字符串。"""
    return "[" + ",".join(str(float(x)) for x in vector) + "]"


def _has_bbox_mode_column(cur):
    """检查 chunks.bbox_mode 是否已由 P6 加列。

    #40 的 bbox_mode 需要表结构变更，P5 没有 docs/03 的编辑权；
    在 P6 加列之前先只写 bbox_*，加列后本函数自动切到带 mode 的 SQL。
    """
    cur.execute(
        "select 1 from information_schema.columns "
        "where table_name = 'chunks' and column_name = 'bbox_mode'"
    )
    return cur.fetchone() is not None


def save_chunks(paper_id, chunks, vectors):
    """先删旧切片，再写入新切片。返回写入条数。

    参数:
        paper_id: papers 表的主键
        chunks: build_chunks() 的结果
        vectors: embed_texts() 的结果，形状 (切片数, 1024)
    """
    if len(chunks) != len(vectors):
        raise ValueError("chunks 与 vectors 数量不一致")

    rows = []
    modes = []
    for i in range(len(chunks)):
        chunk = chunks[i]
        rows.append((
            paper_id,
            chunk["chunk_index"],
            chunk["page"],
            chunk["content"],
            chunk["char_count"],
            chunk.get("bbox_x0"),
            chunk.get("bbox_y0"),
            chunk.get("bbox_x1"),
            chunk.get("bbox_y1"),
            vector_to_string(vectors[i]),
        ))
        modes.append(chunk.get("bbox_mode"))

    with get_connection() as conn:
        with conn.cursor() as cur:
            has_bbox_mode = _has_bbox_mode_column(cur)
            if not has_bbox_mode:
                logger.warning(
                    "chunks.bbox_mode 列不存在，本次只写 bbox_*；"
                    "等 P6 加列后自动写入 bbox_mode"
                )

            # 契约要求：重复解析时先删旧数据
            cur.execute("delete from chunks where paper_id = %s", (paper_id,))

            if has_bbox_mode:
                rows_with_mode = [
                    row[:9] + (mode,) + row[9:]
                    for row, mode in zip(rows, modes)
                ]
                cur.executemany(INSERT_WITH_MODE, rows_with_mode)
            else:
                cur.executemany(INSERT_WITHOUT_MODE, rows)

    return len(rows)
