"""向量化：把文本转成 1024 维向量（bge-m3）。"""

import threading

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-m3"

_model = None   # 全局缓存，只加载一次
_lock = threading.Lock()

def get_model():
    """第一次调用时才加载模型（懒加载，并发时只加载一次）。"""
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = SentenceTransformer(MODEL_NAME)
    return _model

def embed_texts(texts, show_progress_bar=True):
    """把一组文本转成向量。

    参数:
        texts: 字符串列表
        show_progress_bar: 是否显示进度条（单条查询时关掉）

    返回:
        numpy 数组，形状是 (文本数, 1024)
    """
    model = get_model()
    return model.encode(
        texts,
        normalize_embeddings=True,   # 归一化，后面可以直接算余弦相似度
        batch_size=8,
        show_progress_bar=show_progress_bar,
    )
