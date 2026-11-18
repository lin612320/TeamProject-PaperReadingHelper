"""生成 #40 / F6-04 证据：单栏论文 10 条引用 bbox 渲染图 + 对照表。

用法（在 ai-service 目录下）：
    .venv/Scripts/python.exe -m scripts.f6_04_evidence
    .venv/Scripts/python.exe -m scripts.f6_04_evidence data/attention.pdf

输出：
    ai-service/data/f6-04-evidence/q01-page05.png ...
    ai-service/data/f6-04-evidence/report.md
"""

import argparse
import os
import sys

import pymupdf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.db.connection import get_connection
from app.services.ingest import ingest_paper
from app.services.RAG import _build_citations, search_chunks

QUESTION_PRESETS = {
    "attention": [
        "论文提出的 Transformer 模型由哪两部分组成？",
        "多头注意力机制相比单头注意力有什么优势？",
        "位置编码在模型中起什么作用？",
        "编码器层和解码器层分别包含哪些子层？",
        "训练使用了什么优化器和学习率 warmup 策略？",
        "在 WMT 2014 英德翻译任务上 BLEU 分数是多少？",
        "在 WMT 2014 英法翻译任务上 BLEU 分数是多少？",
        "模型训练使用了多少张 GPU、训练了多长时间？",
        "消融实验比较了哪些模型变体？",
        "作者在结论中认为 Transformer 未来可以应用到哪些任务？",
    ],
    "adaptive-rag": [
        "论文提出的 Adaptive-RAG 框架包含哪几个组件？",
        "分类器如何判断查询复杂度？",
        "A、B、C 三个复杂度标签分别代表什么？",
        "与多步方法相比，Adaptive-RAG 的效率如何？",
        "表 3 中 A、B、C 对应的每查询耗时分别是多少？",
        "论文在哪些数据集上做了实验？",
        "自适应策略相比单步和多步检索的准确率如何？",
        "论文的主要贡献有哪三点？",
        "训练分类器使用了什么数据？",
        "论文的局限性是什么？",
    ],
}


def check_bbox_mode_column():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select 1 from information_schema.columns "
                "where table_name = 'chunks' and column_name = 'bbox_mode'"
            )
            return cur.fetchone() is not None


def add_paper(file_path):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into papers (title, filename, file_path) "
                "values (%s, %s, %s) returning id",
                ("__f6_04__", os.path.basename(file_path), file_path),
            )
            return cur.fetchone()[0]


def delete_paper(paper_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from papers where id = %s", (paper_id,))


def render_one(pdf_path, citation, out_path, label):
    doc = pymupdf.open(pdf_path)
    try:
        page = doc[citation["page"] - 1]
        width = page.rect.width
        height = page.rect.height

        rect = pymupdf.Rect(
            citation["bboxX0"] * width,
            citation["bboxY0"] * height,
            citation["bboxX1"] * width,
            citation["bboxY1"] * height,
        )
        if page.rotation:
            rect = rect * page.derotation_matrix

        page.draw_rect(rect, color=(1, 0, 0), width=2)
        page.insert_text(
            (20, 20),
            "%s | page %d | %s" % (label, citation["page"], citation["bboxMode"]),
            fontsize=10,
            color=(1, 0, 0),
        )
        page.get_pixmap(dpi=120).save(out_path)
    finally:
        doc.close()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="生成 F6-04 引用 bbox 证据")
    parser.add_argument(
        "path",
        nargs="?",
        default=os.path.join(BASE_DIR, "data", "attention.pdf"),
        help="PDF 路径，默认 data/attention.pdf",
    )
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print("文件不存在:", args.path)
        sys.exit(1)

    if not check_bbox_mode_column():
        print("chunks.bbox_mode 列不存在，请先执行 ALTER TABLE。")
        sys.exit(1)

    basename = os.path.basename(args.path)
    preset = "adaptive-rag" if "adaptive-rag" in basename else "attention"
    questions = QUESTION_PRESETS[preset]
    evidence_name = "f6-05-evidence" if preset == "adaptive-rag" else "f6-04-evidence"
    case_name = "F6-05" if preset == "adaptive-rag" else "F6-04"

    out_dir = os.path.join(BASE_DIR, "data", evidence_name)
    os.makedirs(out_dir, exist_ok=True)

    paper_id = add_paper(os.path.abspath(args.path))
    print("测试 paper_id:", paper_id, "| preset:", preset)

    rows = []
    try:
        stats = ingest_paper(paper_id, os.path.abspath(args.path))
        print("入库:", stats["chunkCount"], "片")

        used = set()
        for index, question in enumerate(questions, start=1):
            chunks = search_chunks(paper_id, question, top_k=5)
            chosen = None
            for chunk in chunks:
                if chunk["chunk_id"] not in used:
                    chosen = chunk
                    break
            if chosen is None and chunks:
                chosen = chunks[0]
            if chosen is None:
                print("Q%d 没有检索到片段，跳过" % index)
                continue

            used.add(chosen["chunk_id"])
            citation = _build_citations([chosen], 1)[0]
            rows.append({
                "index": index,
                "question": question,
                "citation": citation,
            })
            print(
                "Q%d page=%d bbox=(%s, %s, %s, %s) mode=%s"
                % (
                    index,
                    citation["page"],
                    citation["bboxX0"],
                    citation["bboxY0"],
                    citation["bboxX1"],
                    citation["bboxY1"],
                    citation["bboxMode"],
                )
            )
    finally:
        delete_paper(paper_id)
        print("已清理测试论文")

    report_lines = [
        "# %s 引用 bbox 证据（#40）" % case_name,
        "",
        "- 样本：`%s`" % os.path.basename(args.path),
        "- 问题数：%d" % len(rows),
        "- 说明：红框为 citation 的 bbox；`precise` 表示块级精确框，`block` 为整段降级框。",
        "",
        "| # | 问题 | 页码 | mode | bbox | 引用片段（前 60 字） | PNG |",
        "|---|---|---|---|---|---|---|",
    ]

    for row in rows:
        citation = row["citation"]
        snippet = citation["snippet"].replace("\n", " ").replace("|", "\\|")[:60]
        png_name = "q%02d-page%02d.png" % (row["index"], citation["page"])
        png_path = os.path.join(out_dir, png_name)
        render_one(args.path, citation, png_path, "Q%d" % row["index"])
        report_lines.append(
            "| %d | %s | %d | %s | (%.3f, %.3f, %.3f, %.3f) | %s | %s |"
            % (
                row["index"],
                row["question"],
                citation["page"],
                citation["bboxMode"],
                citation["bboxX0"],
                citation["bboxY0"],
                citation["bboxX1"],
                citation["bboxY1"],
                snippet,
                png_name,
            )
        )

    report_path = os.path.join(out_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    modes = {}
    for row in rows:
        mode = row["citation"]["bboxMode"]
        modes[mode] = modes.get(mode, 0) + 1

    print("\n输出目录:", out_dir)
    print("报告:", report_path)
    print("模式分布:", modes)
    print("共 %d 条引用" % len(rows))


if __name__ == "__main__":
    main()
