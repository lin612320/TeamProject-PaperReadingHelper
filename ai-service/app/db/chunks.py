"""chunks表的写入"""

import logging

from app.db.connection import get_connection

logger = logging.getLogger(__name__)

def vector_to_string(vector):
    """把 1024 个浮点数转成 PostgreSQL 能识别的字符串。"""
    return "[" + ",".join(str(float(x)) for x in vector) + "]"


def _has_column(cur, column_name):
    """检查 chunks 表是否已有指定列（由 P6 负责加列）。"""
    cur.execute(
        "select 1 from information_schema.columns "
        "where table_name = 'chunks' and column_name = %s",
        (column_name,),
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
    orders = []
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
        orders.append(chunk.get("reading_order"))

    with get_connection() as conn:
        with conn.cursor() as cur:
            has_bbox_mode = _has_column(cur, "bbox_mode")
            has_reading_order = _has_column(cur, "reading_order")

            if not has_bbox_mode:
                logger.warning(
                    "chunks.bbox_mode 列不存在，本次只写 bbox_*；"
                    "等 P6 加列后自动写入 bbox_mode"
                )
            if not has_reading_order:
                logger.warning(
                    "chunks.reading_order 列不存在，本次跳过 reading_order；"
                    "等 P6 加列后自动写入（契约 1.3.0）"
                )

            columns = [
                "paper_id", "chunk_index", "page", "content", "char_count",
                "bbox_x0", "bbox_y0", "bbox_x1", "bbox_y1",
            ]
            if has_bbox_mode:
                columns.append("bbox_mode")
            if has_reading_order:
                columns.append("reading_order")
            columns.append("embedding")

            placeholders = []
            for column in columns:
                if column == "embedding":
                    placeholders.append("%s::vector")
                else:
                    placeholders.append("%s")

            sql = "insert into chunks (%s) values (%s)" % (
                ", ".join(columns),
                ", ".join(placeholders),
            )

            values = []
            for i, row in enumerate(rows):
                item = list(row[:9])
                if has_bbox_mode:
                    item.append(modes[i])
                if has_reading_order:
                    item.append(orders[i])
                item.append(row[9])
                values.append(tuple(item))

            # 契约要求：重复解析时先删旧数据
            cur.execute("delete from chunks where paper_id = %s", (paper_id,))
            cur.executemany(sql, values)

    return len(rows)
