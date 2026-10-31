"""chunks表的写入"""

from app.db.connection import get_connection

def vector_to_string(vector):
    """把 1024 个浮点数转成 PostgreSQL 能识别的字符串。"""
    return "[" + ",".join(str(float(x)) for x in vector) + "]"


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
    for i in range(len(chunks)):
        chunk = chunks[i]
        rows.append((
            paper_id,
            chunk["chunk_index"],
            chunk["page"],
            chunk["content"],
            chunk["char_count"],
            vector_to_string(vectors[i]),
        ))

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 契约要求：重复解析时先删旧数据
            cur.execute("delete from chunks where paper_id = %s", (paper_id,))
            cur.executemany(
                "insert into chunks "
                "(paper_id, chunk_index, page, content, char_count, embedding) "
                "values (%s, %s, %s, %s, %s, %s::vector)",
                rows,
            )

    return len(rows)
