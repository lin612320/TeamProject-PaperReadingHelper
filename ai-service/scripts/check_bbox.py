"""开发工具：验证 #40 的 bbox 产出与 #82 的切片/阅读顺序基线。

用法（在 ai-service 目录下）：
    .venv/Scripts/python.exe -m scripts.check_bbox
    .venv/Scripts/python.exe -m scripts.check_bbox data/attention.pdf
    .venv/Scripts/python.exe -m scripts.check_bbox data/attention.pdf --render
    .venv/Scripts/python.exe -m scripts.check_bbox data/attention.pdf --rotation
"""

import argparse
import hashlib
import json
import os
import sys
import tempfile

import pymupdf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.services.chunker import build_chunks
from app.services.pdf_extractor import extract_blocks

# 单栏严格基线：单栏论文的切片内容必须逐字节不变
STRICT_BASELINES = {
    "attention.pdf": (
        77,
        "2ed77607a0f370d6d8cc4e2e3130ff299cedf3fa317b3ab7752ed92d835e8ba1",
    ),
}

# 双栏预期基线：#81 按阅读顺序重排后，chunk 边界会变化；由 #82 人工抽查后冻结。
# 换切片规则或重排规则时必须重新人工确认，不能只看哈希。
EXPECTED_BASELINES = {
    "adaptive-rag.pdf": (
        133,
        "d1f11492f83351a5ed71b663e7c1f2af764184050cdf4d414c1dd4a1cf8c90b3",
    ),
    "query-rewriting.pdf": (
        101,
        "475ae68d591f3d09b72f3be16b844772aa75c2d2bd75f6f9df200de1ddcf7cf9",
    ),
    "rt-detr.pdf": (
        105,
        "e00b3ff22bffd0b7ae1ec0a17ab83d8a699a2a2bc76c7d7e79f6a4ef2ee01c4f",
    ),
}


def content_hash(chunks):
    payload = json.dumps(
        [
            {"i": c["chunk_index"], "p": c["page"], "t": c["content"]}
            for c in chunks
        ],
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def check_one(path, render=False, out_dir=None):
    """检查一篇 PDF 的 bbox；返回失败项数量。"""
    failures = 0
    blocks, page_count = extract_blocks(path)
    chunks = build_chunks(blocks)
    name = os.path.basename(path)

    print("== %s" % path)
    print("页数: %d | 文字块: %d | 切片: %d" % (page_count, len(blocks), len(chunks)))

    # 1. 切片回归：单栏必须逐字节不变；双栏基线是 #81 重排后的预期值
    strict = STRICT_BASELINES.get(name)
    expected = EXPECTED_BASELINES.get(name)
    baseline = strict or expected

    if baseline is not None:
        label = "单栏严格基线" if strict else "双栏预期基线"
        expected_count, expected_hash = baseline
        if len(chunks) != expected_count:
            print("FAIL %s 切片数: 期望 %d，实际 %d"
                  % (label, expected_count, len(chunks)))
            failures += 1
        actual_hash = content_hash(chunks)
        if actual_hash != expected_hash:
            print("FAIL %s 内容哈希不一致" % label)
            print("  期望:", expected_hash)
            print("  实际:", actual_hash)
            failures += 1
        else:
            print("PASS %s（%d 片，哈希一致）" % (label, expected_count))

    # 2. bbox 边界与字段一致性
    valid = 0
    invalid = []
    modes = {}
    for chunk in chunks:
        if chunk["char_count"] != len(chunk["content"]):
            invalid.append((chunk["chunk_index"], "char_count 不一致"))
            continue

        if chunk["bbox_x0"] is None:
            if chunk["bbox_mode"] is not None:
                invalid.append((chunk["chunk_index"], "bbox 为 null 但 bbox_mode 有值"))
            continue

        x0 = chunk["bbox_x0"]
        y0 = chunk["bbox_y0"]
        x1 = chunk["bbox_x1"]
        y1 = chunk["bbox_y1"]
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            invalid.append((chunk["chunk_index"], "bbox 越界或宽高非正"))
            continue
        if chunk["bbox_mode"] not in ("precise", "block"):
            invalid.append((chunk["chunk_index"], "bbox_mode 非法"))
            continue

        valid += 1
        modes[chunk["bbox_mode"]] = modes.get(chunk["bbox_mode"], 0) + 1

    print("bbox 有效: %d / %d | 模式: %s" % (valid, len(chunks), modes or "{}"))
    if valid == 0:
        print("FAIL 没有任何有效 bbox")
        failures += 1

    for chunk_index, reason in invalid:
        print("FAIL chunk %d: %s" % (chunk_index, reason))
        failures += 1

    # 3. 抽样打印，方便肉眼核对
    print("--- 前 5 个 chunk ---")
    for chunk in chunks[:5]:
        print(
            "chunk %d | page %d | chars %d | bbox %s | mode %s"
            % (
                chunk["chunk_index"],
                chunk["page"],
                chunk["char_count"],
                (
                    chunk["bbox_x0"],
                    chunk["bbox_y0"],
                    chunk["bbox_x1"],
                    chunk["bbox_y1"],
                ),
                chunk["bbox_mode"],
            )
        )

    # 4. 渲染带框 PNG
    if render:
        if out_dir is None:
            out_dir = os.path.join(
                BASE_DIR, "data", "bbox_preview", os.path.splitext(name)[0]
            )
        render_boxes(path, chunks, out_dir)

    return failures


def render_boxes(path, chunks, out_dir):
    """把每个 chunk 的 bbox 画在原页面上，输出 PNG 供人工核对。"""
    os.makedirs(out_dir, exist_ok=True)

    by_page = {}
    for chunk in chunks:
        if chunk["bbox_x0"] is None:
            continue
        by_page.setdefault(chunk["page"], []).append(chunk)

    doc = pymupdf.open(path)
    try:
        for page_no in sorted(by_page):
            page = doc[page_no - 1]
            width = page.rect.width
            height = page.rect.height

            for chunk in by_page[page_no]:
                rect = pymupdf.Rect(
                    chunk["bbox_x0"] * width,
                    chunk["bbox_y0"] * height,
                    chunk["bbox_x1"] * width,
                    chunk["bbox_y1"] * height,
                )
                # draw_rect 用未旋转坐标；旋转页先转回去
                if page.rotation:
                    rect = rect * page.derotation_matrix

                color = (1, 0, 0) if chunk["bbox_mode"] == "precise" else (1, 0.55, 0)
                page.draw_rect(rect, color=color, width=1.2)
                try:
                    page.insert_text(
                        (rect.x0 + 1, max(rect.y0 - 1, 6)),
                        str(chunk["chunk_index"]),
                        fontsize=6,
                        color=color,
                    )
                except Exception:
                    # 标注失败不影响 PNG 产出
                    pass

            out_path = os.path.join(out_dir, "page-%02d.png" % page_no)
            page.get_pixmap(dpi=120).save(out_path)
            print("  渲染: %s" % out_path)
    finally:
        doc.close()


def check_rotation(path):
    """把同一页分别旋转 90/180/270 度，确认归一化 bbox 不越界。"""
    print("== 旋转页检查（%s）" % os.path.basename(path))
    failures = 0

    for rotation in (90, 180, 270):
        doc = pymupdf.open(path)
        target = min(2, doc.page_count - 1)
        doc[target].set_rotation(rotation)

        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        try:
            doc.save(tmp.name)
            doc.close()

            blocks, _page_count = extract_blocks(tmp.name)
            chunks = build_chunks(blocks)
            valid = 0
            bad = 0
            for chunk in chunks:
                if chunk["bbox_x0"] is None:
                    continue
                x0, y0 = chunk["bbox_x0"], chunk["bbox_y0"]
                x1, y1 = chunk["bbox_x1"], chunk["bbox_y1"]
                if 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1:
                    valid += 1
                else:
                    bad += 1

            ok = valid > 0 and bad == 0
            print(
                "%s rotation=%d: 切片 %d，有效 bbox %d，越界 %d"
                % ("PASS" if ok else "FAIL", rotation, len(chunks), valid, bad)
            )
            if not ok:
                failures += 1
        finally:
            if not doc.is_closed:
                doc.close()
            os.unlink(tmp.name)

    return failures


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="验证 #40 的 bbox 产出")
    parser.add_argument(
        "path",
        nargs="?",
        default=os.path.join(BASE_DIR, "data", "attention.pdf"),
        help="PDF 路径，默认 data/attention.pdf",
    )
    parser.add_argument("--render", action="store_true", help="渲染带框 PNG")
    parser.add_argument("--out", default=None, help="PNG 输出目录")
    parser.add_argument("--rotation", action="store_true", help="跑旋转页检查")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print("文件不存在:", args.path)
        sys.exit(1)

    failures = check_one(args.path, args.render, args.out)
    if args.rotation:
        failures += check_rotation(args.path)

    if failures:
        print("\n%d 项未通过" % failures)
        sys.exit(1)
    print("\n全部通过")


if __name__ == "__main__":
    main()
