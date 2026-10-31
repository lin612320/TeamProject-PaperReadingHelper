"""开发工具：抽取 PDF 并打印统计，用于验证 #17。

用法（在 ai-service 目录下）：
    .venv/Scripts/python.exe -m scripts.check_pdf_extractor
    .venv/Scripts/python.exe -m scripts.check_pdf_extractor data/xxx.pdf
    .venv/Scripts/python.exe -m scripts.check_pdf_extractor data/attention.pdf 3
"""

import os
import sys

from app.services.pdf_extractor import extract_blocks


def main():
    # 不传参数时，默认检查这篇样本
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = "data/attention.pdf"

    if not os.path.exists(path):
        print("文件不存在:", path, file=sys.stderr)
        sys.exit(1)

    # 可选的第二个参数：要看哪一页的顺序
    target_page = 0
    if len(sys.argv) > 2:
        try:
            target_page = int(sys.argv[2])
        except ValueError:
            print("页号必须是整数:", sys.argv[2], file=sys.stderr)
            sys.exit(2)

    try:
        blocks, total_pages = extract_blocks(path)
    except Exception as e:
        # 命令行是程序最外层，这里兜底是合理的
        print("读取 PDF 失败:", e, file=sys.stderr)
        sys.exit(1)

    print("总页数:", total_pages)
    print("文字块总数:", len(blocks))
    print()

    print("--- 前 3 块 ---")
    for block in blocks[:3]:
        print("第", block["page"], "页，第", block["order"], "块：")
        print(block["text"][:100])
        print()

    # 指定了页号，就打印这一页所有块的顺序
    if target_page > 0:
        print("--- 第", target_page, "页顺序检查 ---")
        for block in blocks:
            if block["page"] == target_page:
                one_line = block["text"].replace("\n", " ")
                print(block["order"], "|", one_line[:60])
        print()

    counts = {}
    for block in blocks:
        page_no = block["page"]
        if page_no not in counts:
            counts[page_no] = 0
        counts[page_no] = counts[page_no] + 1

    print("--- 每页块数 ---")
    for page_no in sorted(counts):
        print("第", page_no, "页:", counts[page_no], "块")


if __name__ == "__main__":
    main()
