"""开发工具：验证向量化输出，用于 #18。"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.services.pdf_extractor import extract_blocks
from app.services.chunker import build_chunks
from app.services.embedder import embed_texts

def main():
    path = os.path.join(BASE_DIR, "data", "attention.pdf")
    blocks, _ = extract_blocks(path)
    chunks = build_chunks(blocks)

    texts = []
    for c in chunks[:3]:
        texts.append(c["content"])

    start = time.time()
    vectors = embed_texts(texts)
    print("编码耗时(秒):", round(time.time() - start, 1))
    print("输出形状:", vectors.shape)
    print("维度:", vectors.shape[1])

    for v in vectors:
        norm = float((v ** 2).sum() ** 0.5)
        print("范数:", round(norm, 4))

if __name__ == "__main__":
    main()
