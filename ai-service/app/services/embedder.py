"""向量化：把文本转成 1024 维向量（bge-m3）。"""

from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-m3"

_model = None   # 全局缓存，只加载一次

def get_model():
    """第一次调用时才加载模型（懒加载）。"""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def embed_texts(texts):
    """把一组文本转成向量。

    参数:
        texts: 字符串列表

    返回:
        numpy 数组，形状是 (文本数, 1024)
    """
    model = get_model()
    return model.encode(
        texts,
        normalize_embeddings=True,   # 归一化，后面可以直接算余弦相似度
        batch_size=8,
        show_progress_bar=True,
    )
