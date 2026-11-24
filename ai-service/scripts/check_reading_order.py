"""开发工具：验证 #81/#82 的 reading_order。

默认跑本地 4 篇样本（data/ 不在仓库里，缺文件会跳过）：

    .venv/Scripts/python.exe -m scripts.check_reading_order

指定 PDF：

    .venv/Scripts/python.exe -m scripts.check_reading_order \
        --pdf data/baseline/adaptive-rag/adaptive-rag.pdf

脚本做三件事：
1. 打印每页“原始块位置 -> 新 reading_order”的对比；
2. 校验块不丢不重、单栏页顺序不变、band/column 顺序正确；
3. 每篇双栏论文抽 5 个 chunk 打印，供人工确认段落连贯、无跨栏拼接。
"""

import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.services.chunker import (
    _block_bbox,
    _order_page_blocks,
    build_chunks,
    build_page_layout,
)
from app.services.pdf_extractor import extract_blocks

DEFAULT_PDFS = [
    os.path.join(BASE_DIR, "data", "attention.pdf"),
    os.path.join(BASE_DIR, "data", "baseline", "adaptive-rag", "adaptive-rag.pdf"),
    os.path.join(BASE_DIR, "data", "baseline", "query-rewriting", "query-rewriting.pdf"),
    os.path.join(BASE_DIR, "data", "baseline", "rt-detr", "rt-detr.pdf"),
]


def load_pages(path):
    blocks, page_count = extract_blocks(path)
    pages = {}
    for block in blocks:
        pages.setdefault(block["page"], []).append(block)
    return pages, page_count, blocks


def _column_of(block, band):
    """返回块在 band 内的栏号：0=左，1=右，-1=跨栏；非双栏带返回 None。"""
    if band["layout"] != "double":
        return None
    bbox = _block_bbox(block)
    if bbox is None:
        return -1
    gutter = band["gutter"]
    if bbox[2] <= gutter:
        return 0
    if bbox[0] >= gutter:
        return 1
    return -1


def _column_label(column):
    if column == 0:
        return "colL"
    if column == 1:
        return "colR"
    if column == -1:
        return "span"
    return "single"


def _block_y(block):
    bbox = _block_bbox(block)
    if bbox is None:
        return 1.0
    return bbox[1]


def check_page_order(page_no, page_blocks, layout, ordered):
    """校验一页的阅读顺序，返回失败项数量。"""
    failures = 0

    ids_before = [id(block) for block in page_blocks]
    ids_after = [id(block) for block, _order in ordered]
    if sorted(ids_before) != sorted(ids_after):
        print("  FAIL p%02d: 块有丢失或重复" % page_no)
        failures += 1

    orders = [order for _block, order in ordered]
    if sorted(orders) != list(range(len(page_blocks))):
        print("  FAIL p%02d: reading_order 不是 0..n-1" % page_no)
        failures += 1

    if layout["layout"] in ("single", "unknown") and ids_after != ids_before:
        print("  FAIL p%02d: %s 页顺序被改变"
              % (page_no, layout["layout"]))
        failures += 1

    info = {}
    for band_index, band in enumerate(layout["bands"]):
        for block in band["blocks"]:
            info[id(block)] = (band_index, _column_of(block, band))

    if len(info) != len(page_blocks):
        print("  FAIL p%02d: 有块未被 band 覆盖" % page_no)
        failures += 1

    band_indices = [info[id(block)][0] for block, _order in ordered if id(block) in info]
    if band_indices != sorted(band_indices):
        print("  FAIL p%02d: band 顺序不是自上而下" % page_no)
        failures += 1

    for band_index, band in enumerate(layout["bands"]):
        band_blocks = [
            (block, order) for block, order in ordered
            if id(block) in info and info[id(block)][0] == band_index
        ]
        if band["layout"] == "double":
            columns = [info[id(block)][1] for block, _order in band_blocks]
            mapped = [2 if column == -1 else column for column in columns]
            if mapped != sorted(mapped):
                print("  FAIL p%02d: band%d 不是先左栏后右栏" % (page_no, band_index))
                failures += 1
        elif layout["layout"] not in ("single", "unknown"):
            # 单栏/unknown 页的硬要求是“保持原始顺序”，上面已经校验；
            # 双栏页里的通栏/单栏带才要求按 y 自上而下。
            ys = [_block_y(block) for block, _order in band_blocks]
            if ys != sorted(ys):
                print("  FAIL p%02d: band%d 不是按 y 自上而下" % (page_no, band_index))
                failures += 1

    return failures


def print_page_detail(page_no, page_blocks, layout, ordered, chunk_count,
                      limit, show_all):
    before_index = {id(block): index for index, block in enumerate(page_blocks)}
    info = {}
    for band_index, band in enumerate(layout["bands"]):
        for block in band["blocks"]:
            info[id(block)] = (band_index, band["layout"],
                               _column_of(block, band))

    print("  p%02d layout=%s bands=%d blocks=%d chunks=%d"
          % (page_no, layout["layout"], len(layout["bands"]),
             len(page_blocks), chunk_count))

    shown = 0
    for block, order in ordered:
        if not show_all and shown >= limit:
            print("    ... 其余 %d 块省略（--all 查看）" % (len(page_blocks) - shown))
            break
        band_index, band_layout, column = info.get(id(block), (-1, "unknown", None))
        if band_layout == "full_width":
            label = "full"
        elif band_layout == "single":
            label = "single"
        else:
            label = _column_label(column)
        bbox = _block_bbox(block)
        y = "?" if bbox is None else "%.2f" % bbox[1]
        text = block.get("text", "").strip().replace("\n", " ")[:44]
        print("    order %-3d before[%-3d] band%d %-6s y=%-5s | %s"
              % (order, before_index.get(id(block), -1), band_index,
                 label, y, text))
        shown += 1


def print_samples(chunks, page_layouts, samples):
    """每篇双栏论文抽若干 chunk，供人工确认段落连贯。"""
    clean_pages = set()
    for page_no, layout in page_layouts.items():
        if (
            layout["layout"] == "double"
            and len(layout["bands"]) == 1
            and layout["bands"][0]["layout"] == "double"
        ):
            clean_pages.add(page_no)

    double_chunks = [
        chunk for chunk in chunks
        if page_layouts.get(chunk["page"], {}).get("layout") == "double"
    ]
    clean_chunks = [chunk for chunk in double_chunks if chunk["page"] in clean_pages]
    # 优先抽“整页只有一条双栏带”的正文页，避免抽样落在表格/图注页上
    pool = clean_chunks if len(clean_chunks) >= samples else double_chunks
    if not pool or samples <= 0:
        return

    step = max(1, len(pool) // samples)
    selected = pool[::step][:samples]

    print("  人工抽查（双栏页 chunk，共 %d 个，抽 %d 个%s）："
          % (len(double_chunks), len(selected),
             "，优先正文页" if pool is clean_chunks else ""))
    for chunk in selected:
        content = chunk["content"].replace("\n", " ")
        print("    page %d | chunk %d | ro %s | %d 字 | %s"
              % (chunk["page"], chunk["chunk_index"], chunk["reading_order"],
                 chunk["char_count"], content[:180]))


def check_pdf(path, limit=12, show_all=False, samples=5):
    if not os.path.exists(path):
        print("文件不存在，跳过: " + path)
        return 0

    pages, page_count, blocks = load_pages(path)
    chunks = build_chunks(blocks)
    chunks_by_page = {}
    for chunk in chunks:
        chunks_by_page.setdefault(chunk["page"], []).append(chunk)

    print("\n== %s（%d 页，%d 块，%d 片）=="
          % (os.path.basename(path), page_count, len(blocks), len(chunks)))

    failures = 0
    page_layouts = {}

    for page_no in sorted(pages):
        page_blocks = pages[page_no]
        layout = build_page_layout(page_blocks)
        page_layouts[page_no] = layout
        ordered = _order_page_blocks(page_blocks, layout)

        failures += check_page_order(page_no, page_blocks, layout, ordered)

        page_chunks = chunks_by_page.get(page_no, [])
        ros = [chunk["reading_order"] for chunk in page_chunks]
        if any(ro is None for ro in ros):
            print("  FAIL p%02d: 有 chunk 缺 reading_order" % page_no)
            failures += 1
        elif any(ros[i] > ros[i + 1] for i in range(len(ros) - 1)):
            print("  FAIL p%02d: chunk 的 reading_order 不是单调不减" % page_no)
            failures += 1

        if layout["layout"] == "double" or show_all:
            print_page_detail(page_no, page_blocks, layout, ordered,
                              len(page_chunks), limit, show_all)
        else:
            print("  p%02d layout=%-6s bands=%d blocks=%d chunks=%d"
                  % (page_no, layout["layout"], len(layout["bands"]),
                     len(page_blocks), len(page_chunks)))

    print_samples(chunks, page_layouts, samples)
    return failures


def main():
    parser = argparse.ArgumentParser(description="检查 #81 reading_order / #82 重排回归")
    parser.add_argument("--pdf", action="append", default=[],
                        help="PDF 路径，可重复传入；默认跑 data/ 下 4 篇样本")
    parser.add_argument("--all", action="store_true",
                        help="打印每页全部块的 before/after 对比")
    parser.add_argument("--limit", type=int, default=12,
                        help="每页默认打印多少个块（--all 时忽略）")
    parser.add_argument("--samples", type=int, default=5,
                        help="每篇双栏论文抽多少个 chunk 供人工检查；0 表示关闭")
    args = parser.parse_args()

    paths = args.pdf
    if not paths:
        paths = [path for path in DEFAULT_PDFS if os.path.exists(path)]
        if not paths:
            print("data/ 下没有找到默认样本，请用 --pdf 指定 PDF")
            sys.exit(1)

    failures = 0
    for path in paths:
        failures += check_pdf(path, args.limit, args.all, args.samples)

    if failures:
        print("\n失败 %d 项" % failures)
        sys.exit(1)
    print("\n全部通过")


if __name__ == "__main__":
    main()
