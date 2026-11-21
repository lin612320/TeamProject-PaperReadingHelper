"""开发工具：验证 #79 切带 / #80 栏缝检测。

默认只跑合成页（不依赖 data/，可直接进 CI）：

    .venv/Scripts/python.exe -m scripts.check_layout

附加真实 PDF 诊断（data/ 不在仓库里，需要本地有文件）：

    .venv/Scripts/python.exe -m scripts.check_layout \
        --pdf data/baseline/adaptive-rag/adaptive-rag.pdf \
        --pdf data/baseline/rt-detr/rt-detr.pdf
"""

import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.services.chunker import (
    _is_double_column,
    build_page_layout,
)


def make_block(text, x0, y0, x1, y1, page=1):
    """构造一个与 extract_blocks() 字段对齐的合成块。"""
    return {
        "page": page,
        "order": 0,
        "text": text,
        "x0": x0,
        "y0": y0,
        "x1": x1,
        "y1": y1,
        "bbox_x0": x0,
        "bbox_y0": y0,
        "bbox_x1": x1,
        "bbox_y1": y1,
    }


LONG_TEXT = "This is a sufficiently long paragraph for layout detection."


def column_blocks(rows=4, y_start=0.10, y_step=0.10,
                  left=(0.10, 0.48), right=(0.52, 0.90)):
    """左右成对生成一页双栏正文块。"""
    blocks = []
    for i in range(rows):
        y0 = y_start + i * y_step
        blocks.append(make_block("left column paragraph %d %s" % (i, LONG_TEXT),
                                 left[0], y0, left[1], y0 + 0.06))
        blocks.append(make_block("right column paragraph %d %s" % (i, LONG_TEXT),
                                 right[0], y0, right[1], y0 + 0.06))
    return blocks


def synthetic_cases():
    """返回 [(用例名, blocks, 期望)]。

    期望字段:
        layout:     "single" / "double"
        bands:      band 数
        fullWidth:  每个 band 的 full_width 标志
        gutters:    每个 band 的 gutter 期望；None 表示没有栏缝，
                    (lo, hi) 表示栏缝应落在这个闭区间
    """
    cases = []

    # 1. 单栏页，但正文块很宽（0.80）。不能被“宽度 >0.75”误切。
    blocks = []
    for i in range(6):
        y0 = 0.10 + i * 0.10
        blocks.append(make_block("wide single column paragraph %d %s" % (i, LONG_TEXT),
                                 0.10, y0, 0.90, y0 + 0.06))
    cases.append(("single_column_wide", blocks, {
        "layout": "single", "bands": 1, "fullWidth": [False],
        "gutters": [None],
    }))

    # 2. 干净双栏页。
    cases.append(("two_column", column_blocks(4), {
        "layout": "double", "bands": 1, "fullWidth": [False],
        "gutters": [(0.49, 0.51)],
    }))

    # 3. 通栏标题 + 双栏正文 → 2 个带。
    blocks = [make_block("A full width paper title for layout detection",
                         0.10, 0.05, 0.90, 0.08)]
    blocks.extend(column_blocks(4, y_start=0.15))
    cases.append(("title_two_column", blocks, {
        "layout": "double", "bands": 2, "fullWidth": [True, False],
        "gutters": [None, (0.49, 0.51)],
    }))

    # 4. 双栏 → 通栏表格 → 双栏 → 3 个带。
    blocks = column_blocks(2, y_start=0.10)
    blocks.append(make_block("Table 1: full width table caption for layout detection",
                             0.10, 0.35, 0.90, 0.38))
    blocks.extend(column_blocks(2, y_start=0.45))
    cases.append(("table_between_columns", blocks, {
        "layout": "double", "bands": 3, "fullWidth": [False, True, False],
        "gutters": [(0.49, 0.51), None, (0.49, 0.51)],
    }))

    # 5. 偏中线的栏缝：必须找到 0.44 左右，而不是写死 0.50。
    cases.append(("offset_gutter",
                  column_blocks(4, left=(0.08, 0.40), right=(0.48, 0.92)), {
                      "layout": "double", "bands": 1, "fullWidth": [False],
                      "gutters": [(0.40, 0.48)],
                  }))

    # 6. 0.74 宽表格行（不到 75%）+ 双栏正文。
    #    表格行必须靠“跨候选栏缝”成为屏障，否则会污染正文的投影。
    blocks = [make_block("Table row spanning both columns but below 75 percent",
                         0.13, 0.05, 0.87, 0.07)]
    blocks.extend(column_blocks(4, y_start=0.15))
    cases.append(("wide_table_074", blocks, {
        "layout": "double", "bands": 2, "fullWidth": [True, False],
        "gutters": [None, (0.49, 0.51)],
    }))

    # 7. 单栏页里的窄块：宽度不足，但左右没有分栏证据，不能误判。
    blocks = []
    for i in range(6):
        y0 = 0.10 + i * 0.10
        blocks.append(make_block("narrow single column paragraph %d %s" % (i, LONG_TEXT),
                                 0.30, y0, 0.70, y0 + 0.06))
    cases.append(("false_positive_single", blocks, {
        "layout": "single", "bands": 1, "fullWidth": [False],
        "gutters": [None],
    }))

    # 8. 连续通栏行（表格多行）应合并成一个带，而不是每行一个带。
    blocks = [
        make_block("wide table row zero for layout detection", 0.10, 0.05, 0.90, 0.07),
        make_block("wide table row one for layout detection", 0.10, 0.10, 0.90, 0.12),
        make_block("wide table row two for layout detection", 0.10, 0.15, 0.90, 0.17),
    ]
    blocks.extend(column_blocks(4, y_start=0.25))
    cases.append(("consecutive_full_width", blocks, {
        "layout": "double", "bands": 2, "fullWidth": [True, False],
        "gutters": [None, (0.49, 0.51)],
    }))

    # 9. 非法 bbox 不能导致崩溃或丢块。
    blocks = column_blocks(4)
    broken = make_block("broken", 0.0, 0.0, 0.0, 0.0)
    broken["bbox_x0"] = None
    broken["bbox_y0"] = None
    broken["bbox_x1"] = None
    broken["bbox_y1"] = None
    blocks.insert(0, broken)
    cases.append(("invalid_bbox", blocks, {
        "layout": "double", "bands": 1, "fullWidth": [False],
        "gutters": [(0.49, 0.51)],
    }))

    return cases


def _expect(condition, message):
    if condition:
        return 0
    print("  FAIL " + message)
    return 1


def check_case(name, blocks, expected):
    """跑一个合成用例，返回失败项数量。"""
    result = build_page_layout(blocks)
    bands = result["bands"]
    failures = 0

    failures += _expect(
        result["layout"] == expected["layout"],
        "%s: layout 期望 %s，实际 %s" % (name, expected["layout"], result["layout"]),
    )
    failures += _expect(
        len(bands) == expected["bands"],
        "%s: band 数期望 %d，实际 %d" % (name, expected["bands"], len(bands)),
    )

    actual_full = [band["full_width"] for band in bands]
    failures += _expect(
        actual_full == expected["fullWidth"],
        "%s: full_width 期望 %s，实际 %s" % (name, expected["fullWidth"], actual_full),
    )

    for i, want in enumerate(expected["gutters"]):
        got = bands[i]["gutter"] if i < len(bands) else None
        if want is None:
            failures += _expect(
                got is None,
                "%s: band%d gutter 期望 None，实际 %s" % (name, i, got),
            )
        else:
            lo, hi = want
            failures += _expect(
                got is not None and lo <= got <= hi,
                "%s: band%d gutter 期望 %s~%s，实际 %s" % (name, i, lo, hi, got),
            )

    ids_in = [id(block) for block in blocks]
    ids_out = [id(block) for band in bands for block in band["blocks"]]
    failures += _expect(
        sorted(ids_in) == sorted(ids_out),
        "%s: 块有丢失或重复（输入 %d，输出 %d）" % (name, len(ids_in), len(ids_out)),
    )

    if expected["layout"] == "single":
        failures += _expect(
            ids_out == ids_in,
            "%s: 单栏页必须保持原始块顺序" % name,
        )

    status = "PASS" if failures == 0 else "FAIL"
    gutters = [band["gutter"] for band in bands]
    print("[%s] %s layout=%s bands=%d gutters=%s"
          % (status, name, result["layout"], len(bands), gutters))
    return failures


def run_synthetic():
    print("== 合成页用例 ==")
    failures = 0
    for name, blocks, expected in synthetic_cases():
        failures += check_case(name, blocks, expected)
    return failures


def load_pdf_pages(path):
    from app.services.pdf_extractor import extract_blocks

    blocks, page_count = extract_blocks(path)
    pages = {}
    for block in blocks:
        pages.setdefault(block["page"], []).append(block)
    return pages, page_count


def check_pdf(path, verbose=False):
    """真实 PDF 诊断：打印每页的带与栏缝，只校验结构不变量。"""
    pages, page_count = load_pdf_pages(path)
    print("\n== PDF: %s（%d 页）==" % (path, page_count))

    failures = 0
    counts = {"single": 0, "double": 0, "unknown": 0}

    for page_no in sorted(pages):
        page_blocks = pages[page_no]
        result = build_page_layout(page_blocks)
        bands = result["bands"]
        layout = result["layout"]
        counts[layout] = counts.get(layout, 0) + 1

        ids_in = [id(block) for block in page_blocks]
        ids_out = [id(block) for band in bands for block in band["blocks"]]
        if sorted(ids_in) != sorted(ids_out):
            print("  FAIL p%02d: 块有丢失或重复" % page_no)
            failures += 1

        if any(len(band["blocks"]) == 0 for band in bands):
            print("  FAIL p%02d: 存在空 band" % page_no)
            failures += 1

        last_y0 = None
        for band in bands:
            if band["gutter"] is not None and not (0.35 <= band["gutter"] <= 0.65):
                print("  FAIL p%02d: gutter 越界 %s" % (page_no, band["gutter"]))
                failures += 1
            if band["y0"] is not None:
                if last_y0 is not None and band["y0"] < last_y0 - 1e-9:
                    print("  FAIL p%02d: band 顺序不是自上而下" % page_no)
                    failures += 1
                last_y0 = band["y0"]

        legacy = _is_double_column(page_blocks)
        note = ""
        if legacy != (layout == "double"):
            note = "  NOTE legacy_double=%s" % legacy

        if verbose:
            print("  p%02d blocks=%d" % (page_no, len(page_blocks)))
            for i, band in enumerate(bands):
                first = ""
                if band["blocks"]:
                    first = band["blocks"][0]["text"][:30].replace("\n", " ")
                print("    band%d full_width=%s y=%s-%s gutter=%s n=%d %r"
                      % (i, band["full_width"], band["y0"], band["y1"],
                         band["gutter"], len(band["blocks"]), first))
        else:
            print("  p%02d layout=%s bands=%d full_width=%s gutters=%s%s"
                  % (page_no, layout, len(bands),
                     [band["full_width"] for band in bands],
                     [band["gutter"] for band in bands], note))

    print("  汇总：single=%d double=%d unknown=%d，结构失败=%d"
          % (counts.get("single", 0), counts.get("double", 0),
             counts.get("unknown", 0), failures))
    return failures


def main():
    parser = argparse.ArgumentParser(description="检查 #79 切带 / #80 栏缝检测")
    parser.add_argument("--pdf", action="append", default=[],
                        help="真实 PDF 路径，可重复传入")
    parser.add_argument("--verbose", action="store_true",
                        help="打印每个 band 的详细信息")
    args = parser.parse_args()

    failures = run_synthetic()
    for path in args.pdf:
        if not os.path.exists(path):
            print("文件不存在: " + path)
            failures += 1
            continue
        failures += check_pdf(path, args.verbose)

    if failures:
        print("\n失败 %d 项" % failures)
        sys.exit(1)
    print("\n全部通过")


if __name__ == "__main__":
    main()
