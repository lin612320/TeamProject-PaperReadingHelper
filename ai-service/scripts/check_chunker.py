"""开发工具：验证切片结果，用于 #18。"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.services.pdf_extractor import extract_blocks
from app.services.chunker import build_chunks


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = os.path.join(BASE_DIR, "data", "attention.pdf")

    if not os.path.exists(path):
        print("文件不存在:", path)
        sys.exit(1)

    blocks, total_pages = extract_blocks(path)
    chunks = build_chunks(blocks)

    print("页数:", total_pages)
    print("文字块:", len(blocks))
    print("切片数:", len(chunks))

    sizes = []
    for c in chunks:
        sizes.append(c["char_count"])
    print("字数 最小/最大/平均:", min(sizes), max(sizes), sum(sizes) // len(sizes))

    per_page = {}
    for c in chunks:
        p = c["page"]
        if p not in per_page:
            per_page[p] = 0
        per_page[p] = per_page[p] + 1
    print("每页切片数:", per_page)

    print()
    print("--- 前 3 个切片 ---")
    for c in chunks[:3]:
        print("chunk_index:", c["chunk_index"], "| page:", c["page"], "| 字数:", c["char_count"])
        print(c["content"][:150])
        print()


if __name__ == "__main__":
    main()
