"""DPF解析及入库
手段：调用 pdf_extractor.py、chunker.py 和 embedder.py 中已实现的方法
流程：.pdf -> 抽取 -> 切片 -> 向量化 -> 入库
"""

import os
import time
from app.services.pdf_extractor import extract_blocks
from app.services.chunker import build_chunks
from app.services.embedder import embed_texts
from app.db.chunks import save_chunks

class IngestError(Exception):
    """PDF解析异常处理类
    
    契约：
        返回带内部错误码的异常。

    作用：
        路由层据此返回 HTTP 状态码。
    """

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message

def ingest_paper(paper_id, file_path):
    """PDF完整解析流程：抽取、切片、向量化和入库
    参数：
        paper_id: 分配的论文号（论文唯一性标识）
        file_path：论文路径
    返回：
        统计信息组。
    """
    start = time.time()

    # 抽取
    if not os.path.isfile(file_path):
        raise IngestError("FILE_NOT_FOUND", "PDF 文件不存在: " + str(file_path))
    try:
        blocks, page_count = extract_blocks(file_path)
    except FileNotFoundError:
        raise IngestError("FILE_NOT_FOUND", "PDF 文件不存在: " + str(file_path))
    except Exception:
        raise IngestError("NOT_PDF", "无法解析该文件，可能不是合法 PDF")

    # 切片
    chunks = build_chunks(blocks)
    if len(chunks) == 0:
        raise IngestError("NOT_PDF", "PDF 中没有可用的文字")

    # 向量化
    texts = []
    for c in chunks:
        texts.append(c["content"])
    try:
        vectors = embed_texts(texts)
    except Exception as e:
        raise IngestError("EMBEDDING_FAILED", "向量化失败: " + str(e))

    # 入库
    chunk_count = save_chunks(paper_id, chunks, vectors)
    elapsed_ms = int((time.time() - start) * 1000)
    return {
        "paperId": paper_id,
        "parseStatus": "ready",
        "pageCount": page_count,
        "chunkCount": chunk_count,
        "vectorDim": int(vectors.shape[1]),
        "elapsedMs": elapsed_ms,
    }
