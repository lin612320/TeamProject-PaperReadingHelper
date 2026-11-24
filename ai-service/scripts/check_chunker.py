"""开发工具：验证切片结果，用于 #18。"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.services.pdf_extractor import extract_blocks
from app.services.chunker import build_chunks
from scripts.check_bbox import STRICT_BASELINES, content_hash


def check_strict_baseline(path, chunks):
    """单栏论文的严格基线：切片内容必须逐字节不变。"""
    baseline = STRICT_BASELINES.get(os.path.basename(path))
    if baseline is None:
        return 0

    expected_count, expected_hash = baseline
    failures = 0
    if len(chunks) != expected_count:
        print("FAIL 单栏严格基线切片数: 期望 %d，实际 %d"
              % (expected_count, len(chunks)))
        failures += 1

    actual_hash = content_hash(chunks)
    if actual_hash != expected_hash:
        print("FAIL 单栏严格基线内容哈希不一致")
        print("  期望:", expected_hash)
        print("  实际:", actual_hash)
        failures += 1
    else:
        print("PASS 单栏严格基线（%d 片，哈希一致）" % expected_count)
    return failures


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
    failures = check_strict_baseline(path, chunks)

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

    if failures:
        print("\n%d 项未通过" % failures)
        sys.exit(1)


if __name__ == "__main__":
    main()
