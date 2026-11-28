"""开发工具：按 F3 抽样题库批量评估问答接口（#20）。

支持多篇样本论文：读取题库 → 校验每篇 PDF 哈希 → 逐篇入库解析
→ 逐题调用 /internal/qa/ask → 自动核对页码与片段 → 输出 JSON / Markdown。

需要先启动服务：
    .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

用法：
    .venv/Scripts/python.exe -m scripts.eval_qa [--bank 题库] [--out 输出目录] [--label 轮次]
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

import pymupdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from app.db.connection import get_connection

BASE_URL = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_BANK = os.path.join(REPO_ROOT, "docs", "alpha", "测试", "F3抽样题库.md")
DEFAULT_OVERVIEW_BANK = os.path.join(REPO_ROOT, "docs", "测试", "Beta85概览题库.md")
DEFAULT_OUT = os.path.join(REPO_ROOT, "docs", "测试")
NO_ANSWER = "本文未涉及该内容"


def call(method, path, body=None, timeout=120):
    """发一个 HTTP 请求，返回 (状态码, JSON 响应)。"""
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw}
    except urllib.error.URLError as e:
        print("无法连接 ai-service (%s): %s" % (BASE_URL, e.reason))
        print("请先启动服务: .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000")
        sys.exit(1)


def split_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def clean_cell(cell):
    return cell.strip().strip("`").strip()


def parse_bank(path):
    """解析多论文题库。"""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    papers, questions, negatives = {}, [], []
    section = ""

    for line in lines:
        if line.startswith("## "):
            section = line.strip()
            continue
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = split_row(line)
        if not cells:
            continue

        if section.startswith("## 一、样本论文") and re.fullmatch(r"[A-Z]", cells[0]):
            if len(cells) < 5:
                continue
            papers[cells[0]] = {
                "title": cells[1],
                "source": cells[2],
                "path": clean_cell(cells[3]),
                "sha256": clean_cell(cells[4]).lower(),
            }

        elif section.startswith("## 四、题目") and re.fullmatch(r"[A-Z]\d+", cells[0]):
            if len(cells) < 6:
                continue
            pages = [int(p) for p in re.findall(r"p(\d+)", cells[4])]
            if not pages:
                raise ValueError("题目缺少标准页: " + line)
            questions.append({
                "id": cells[0],
                "difficulty": cells[1],
                "paper": cells[2],
                "question": cells[3],
                "standardPages": pages,
                "evidence": cells[5],
            })

        elif section.startswith("## 五、未涉及题") and re.fullmatch(r"N\d+", cells[0]):
            if len(cells) < 3:
                continue
            negatives.append({
                "id": cells[0],
                "paper": cells[1],
                "question": cells[2],
            })

    if not papers or not questions:
        raise ValueError("题库解析失败：缺少论文或题目")
    for item in questions + negatives:
        if item["paper"] not in papers:
            raise ValueError("题目引用了未声明的论文: " + item["paper"])
    return papers, questions, negatives


def parse_overview_bank(path, papers):
    """解析 #85 的五道概览题；Alpha 题库保持不变。"""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    questions = []
    section = ""
    for line in lines:
        if line.startswith("## "):
            section = line.strip()
            continue
        if not section.startswith("## 概览题") or not line.startswith("|") or line.startswith("|---"):
            continue
        cells = split_row(line)
        if not cells or not re.fullmatch(r"O\d+", cells[0]):
            continue
        if len(cells) < 6:
            raise ValueError("概览题字段不足: " + line)
        pages = [int(p) for p in re.findall(r"p(\d+)", cells[4], re.IGNORECASE)]
        if not pages:
            raise ValueError("概览题缺少标准页: " + line)
        questions.append({
            "id": cells[0],
            "difficulty": cells[1],
            "paper": cells[2],
            "question": cells[3],
            "standardPages": pages,
            "evidence": cells[5],
        })

    if len(questions) != 5:
        raise ValueError("#85 概览题应为 5 道，实际 %d 道" % len(questions))
    for item in questions:
        if item["paper"] not in papers:
            raise ValueError("概览题引用了未声明的论文: " + item["paper"])
    return questions


def file_hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def norm_text(text):
    text = text.replace("­", "")
    text = re.sub(r"-\s*\n\s*", "", text)
    return re.sub(r"\s+", "", text).lower()


def load_page_texts(path):
    with pymupdf.open(path) as doc:
        return [norm_text(doc[i].get_text()) for i in range(doc.page_count)]


def git_commit():
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return ""


def add_paper(title, file_path):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into papers (title, filename, file_path) "
                "values (%s, %s, %s) returning id",
                (title, os.path.basename(file_path), file_path),
            )
            return cur.fetchone()[0]


def delete_paper(paper_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from papers where id = %s", (paper_id,))


def ask(paper_id, question):
    return call(
        "POST",
        "/internal/qa/ask",
        {"paperId": paper_id, "question": question, "topK": 3, "maxCitations": 3},
        timeout=40,
    )


def evaluate_questions(paper_id, questions, page_texts):
    results = []
    for item in questions:
        status, body = ask(paper_id, item["question"])
        citations = body.get("citations") or []
        answer = str(body.get("answer", "")).strip()
        pages = [c.get("page") for c in citations]

        page_hit = False
        snippet_ok = False
        for c in citations:
            page_no = c.get("page")
            if page_no not in item["standardPages"]:
                continue
            page_hit = True
            snippet = str(c.get("snippet") or "")
            if 1 <= page_no <= len(page_texts) and norm_text(snippet) in page_texts[page_no - 1]:
                snippet_ok = True

        answered = status == 200 and answer != "" and NO_ANSWER not in answer
        auto_hit = bool(page_hit and snippet_ok and answered)
        results.append({
            "id": item["id"],
            "difficulty": item["difficulty"],
            "paper": item["paper"],
            "question": item["question"],
            "standardPages": item["standardPages"],
            "status": status,
            "answer": answer,
            "returnedPages": pages,
            "pageHit": page_hit,
            "snippetMatch": snippet_ok,
            "answered": answered,
            "autoHit": auto_hit,
            "manualFabricated": None,
            "manualHit": None,
            "elapsedMs": body.get("elapsedMs"),
            "citations": citations,
        })
        print(
            "%-4s %-2s %-2s 标准 %-8s 返回 %-14s 页码=%-5s 片段=%-5s 自动=%s"
            % (item["id"], item["difficulty"], item["paper"], item["standardPages"],
               pages, page_hit, snippet_ok, auto_hit)
        )
    return results


def evaluate_negatives(paper_id, negatives):
    results = []
    for item in negatives:
        status, body = ask(paper_id, item["question"])
        answer = str(body.get("answer", "")).strip()
        citations = body.get("citations") or []
        passed = status == 200 and answer == NO_ANSWER and len(citations) == 0
        results.append({
            "id": item["id"],
            "paper": item["paper"],
            "question": item["question"],
            "status": status,
            "answer": answer,
            "citationCount": len(citations),
            "passed": passed,
        })
        print("%-4s 未涉及：回答=%s citations=%d 通过=%s"
              % (item["id"], answer, len(citations), passed))
    return results


def write_outputs(results, negatives, meta, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    date = datetime.date.today().isoformat()
    label = meta.get("label", "")
    suffix = ("-" + label) if label else ""
    auto_hits = sum(1 for r in results if r["autoHit"])
    negative_passed = sum(1 for r in negatives if r["passed"])

    payload = dict(meta)
    payload.update({
        "date": date,
        "autoHits": auto_hits,
        "total": len(results),
        "negativePassed": negative_passed,
        "negativeTotal": len(negatives),
        "note": "autoHit 不含「答案是否编造」；该列与最终命中需人工确认。",
        "results": results,
        "negatives": negatives,
    })
    json_path = os.path.join(out_dir, "F3抽样结果-%s%s.json" % (date, suffix))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    md_path = os.path.join(out_dir, "F3抽样结果-%s%s.md" % (date, suffix))
    lines = [
        "# F3 抽样评估结果（%s%s）" % (date, (" / " + label) if label else ""),
        "",
        "- 判定口径：三条件（不编造 + 至少一条页码正确 + 片段能在该页找到）",
        "- 抽样：%d 题，通过线 ≥ 7；未涉及题单独统计，要求 100%%" % len(results),
        "- git commit：`%s`" % (meta.get("gitCommit") or "unknown"),
        "",
        "## 10 题命中表",
        "",
        "| 题号 | 难度 | 论文 | 标准页 | 引用页码 | 答案是否编造 | 该页能否支撑 | 命中 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            "| %s | %s | %s | %s | %s | 待人工 | %s | %s |"
            % (
                r["id"], r["difficulty"], r["paper"], r["standardPages"],
                r["returnedPages"],
                "是" if r["snippetMatch"] and r["pageHit"] else "否",
                "待人工（自动：%s）" % ("通过" if r["autoHit"] else "不通过"),
            )
        )
    lines += [
        "",
        "**自动命中（不含编造判断）：%d / %d**" % (auto_hits, len(results)),
        "",
        "## 未涉及题",
        "",
        "| 编号 | 论文 | 回答 | citations 数 | 通过 |",
        "|---|---|---|---|---|",
    ]
    for r in negatives:
        lines.append(
            "| %s | %s | %s | %d | %s |"
            % (r["id"], r["paper"], r["answer"], r["citationCount"],
               "是" if r["passed"] else "否")
        )
    lines += [
        "",
        "**未涉及通过：%d / %d**（要求 100%%）" % (negative_passed, len(negatives)),
        "",
        "> 最终结论需人工确认「答案是否编造」；未涉及题单独统计，不计入 70%。",
    ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return json_path, md_path


def write_beta85_outputs(overview_results, alpha_results, negatives, meta, out_dir):
    """写出 #85 三组当前结果，并保留人工复核状态，避免把自动命中冒充最终命中。"""
    os.makedirs(out_dir, exist_ok=True)
    date = datetime.date.today().isoformat()
    suffix = ("-" + meta["label"]) if meta.get("label") else ""
    groups = {
        "overview": {
            "hitsAuto": sum(1 for r in overview_results if r["autoHit"]),
            "total": len(overview_results),
            "required": 4,
            "autoThresholdMet": sum(1 for r in overview_results if r["autoHit"]) >= 4,
            "manualReviewPending": any(r["manualHit"] is None for r in overview_results),
        },
        "alpha": {
            "hitsAuto": sum(1 for r in alpha_results if r["autoHit"]),
            "total": len(alpha_results),
            "required": 9,
            "autoThresholdMet": sum(1 for r in alpha_results if r["autoHit"]) >= 9,
            "manualReviewPending": any(r["manualHit"] is None for r in alpha_results),
        },
        "negative": {
            "passed": sum(1 for r in negatives if r["passed"]),
            "total": len(negatives),
            "required": len(negatives),
        },
    }
    payload = {
        **meta,
        "date": date,
        "baseline": {
            "overview": "改动前无 O1-O5 同题前测；Alpha 原 B3 曾出现概括题拒答，不折算为 0/5。",
            "alpha": {"hits": 9, "total": 10,
                      "source": "docs/alpha/测试/F3抽样结果-2026-11-05-3papers.md"},
            "negative": {"passed": 3, "total": 3,
                         "source": "docs/alpha/测试/F3抽样结果-2026-11-05-3papers.md"},
        },
        "groups": groups,
        "overviewResults": overview_results,
        "alphaResults": alpha_results,
        "negativeResults": negatives,
        "note": "hitsAuto 只校验答案非拒答、引用页码与片段；最终命中仍须人工确认不编造并填写 manualHit。",
    }
    json_path = os.path.join(out_dir, "Beta85回归-%s%s.json" % (date, suffix))
    md_path = os.path.join(out_dir, "Beta85回归-%s%s.md" % (date, suffix))
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    lines = [
        "# #85 召回回归三组结果（%s%s）" %
        (date, (" / " + meta["label"]) if meta.get("label") else ""),
        "",
        "## 改动前基线",
        "",
        "- 概览组：无 O1–O5 同题前测；Alpha 原 B3 曾出现概括题拒答，不能当作本组 0/5。",
        "- Alpha 原 10 题：**9/10**；未涉及题：**3/3**。来源：`docs/alpha/测试/F3抽样结果-2026-11-05-3papers.md`。",
        "",
        "## 改动后结果",
        "",
        "| 组别 | 自动校验 | 验收线 | 状态 |",
        "|---|---:|---:|---|",
        "| 概览 O1–O5 | %(overview_auto)d/5 | ≥4/5 | %(overview_state)s |" % {
            "overview_auto": groups["overview"]["hitsAuto"],
            "overview_state": (
                "自动校验未达线" if not groups["overview"]["autoThresholdMet"]
                else "待人工复核答案是否编造" if groups["overview"]["manualReviewPending"]
                else "人工已复核"
            ),
        },
        "| Alpha 原题 | %(alpha_auto)d/10 | ≥9/10 | %(alpha_state)s |" % {
            "alpha_auto": groups["alpha"]["hitsAuto"],
            "alpha_state": (
                "自动校验未达线" if not groups["alpha"]["autoThresholdMet"]
                else "待人工复核答案是否编造" if groups["alpha"]["manualReviewPending"]
                else "人工已复核"
            ),
        },
        "| 未涉及题 | %(negative_passed)d/%(negative_total)d | 全部拒答 | %(negative_state)s |" % {
            "negative_passed": groups["negative"]["passed"],
            "negative_total": groups["negative"]["total"],
            "negative_state": "通过" if groups["negative"]["passed"] == groups["negative"]["total"] else "未通过",
        },
        "",
        "> 自动命中不等同于最终命中。请按 `docs/alpha/测试/命中率判定口径.md` 人工核对答案是否编造，并在 JSON 中填写每题 `manualHit` 后确认前两组最终命中数。",
        "",
        "## 概览题逐题记录",
        "",
        "| 题号 | 答案 | 引用页码 | 页码/片段自动校验 | 人工最终命中 |",
        "|---|---|---|---|---|",
    ]
    for r in overview_results:
        answer = re.sub(r"\s+", " ", str(r["answer"])).replace("|", "/")
        lines.append("| %s | %s | %s | %s | 待复核 |" % (
            r["id"], answer, r["returnedPages"],
            "通过" if r["autoHit"] else "不通过",
        ))
    lines += ["", "## Alpha 原 10 题逐题记录", "",
              "| 题号 | 答案 | 引用页码 | 页码/片段自动校验 | 人工最终命中 |",
              "|---|---|---|---|---|"]
    for r in alpha_results:
        answer = re.sub(r"\s+", " ", str(r["answer"])).replace("|", "/")
        lines.append("| %s | %s | %s | %s | 待复核 |" % (
            r["id"], answer, r["returnedPages"],
            "通过" if r["autoHit"] else "不通过",
        ))
    lines += ["", "## 未涉及题逐题记录", "",
              "| 题号 | 答案 | citations 数 | 拒答校验 |", "|---|---|---:|---|"]
    for r in negatives:
        answer = str(r["answer"]).replace("|", "/").replace("\n", " ")
        lines.append("| %s | %s | %d | %s |" % (
            r["id"], answer, r["citationCount"],
            "通过" if r["passed"] else "不通过",
        ))
    lines += ["", "- 服务地址：`%s`" % meta["baseUrl"],
              "- git commit：`%s`" % (meta.get("gitCommit") or "unknown"),
              "- 逐题答案和引用详情见同名 JSON 文件。"]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return json_path, md_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", default=DEFAULT_BANK)
    parser.add_argument("--out", default=DEFAULT_OUT)
    parser.add_argument("--label", default="", help="结果文件后缀，如 round1/round2")
    parser.add_argument("--beta85", action="store_true",
                        help="运行 #85 三组回归：5 道概览题 + Alpha 原 10 题 + 3 道未涉及题")
    parser.add_argument("--overview-bank", default=DEFAULT_OVERVIEW_BANK,
                        help="#85 概览题题库路径")
    args = parser.parse_args()

    papers, questions, negatives = parse_bank(args.bank)
    overview_questions = parse_overview_bank(args.overview_bank, papers) if args.beta85 else []
    print("题库: %d 篇论文 / %d 题 / %d 个未涉及题%s"
          % (len(papers), len(questions), len(negatives),
             " / %d 道概览题" % len(overview_questions) if args.beta85 else ""))

    # 校验每篇 PDF 存在且哈希一致
    for code, paper in papers.items():
        path = os.path.join(REPO_ROOT, paper["path"])
        if not os.path.exists(path):
            print("文件不存在:", path)
            sys.exit(1)
        actual = file_hash(path)
        if paper["sha256"] and paper["sha256"] != actual:
            print("PDF 与题库声明的 SHA256 不一致:", code)
            print("  题库:", paper["sha256"])
            print("  实际:", actual)
            sys.exit(1)
        paper["absPath"] = path
        paper["actualHash"] = actual
        paper["pageTexts"] = load_page_texts(path)
        print("哈希通过 %s: %s" % (code, actual))

    status, health = call("GET", "/internal/health", timeout=10)
    if status != 200 or not health.get("dbReady"):
        print("服务未就绪:", status, health)
        sys.exit(1)

    paper_ids = {}
    meta_papers = {}
    all_results, all_negatives, all_overview_results = [], [], []
    try:
        for code, paper in papers.items():
            paper_id = add_paper("__f3_%s__" % code.lower(), paper["absPath"])
            paper_ids[code] = paper_id
            status, body = call(
                "POST",
                "/internal/papers/parse",
                {"paperId": paper_id, "filePath": paper["absPath"]},
                timeout=600,
            )
            if status != 200:
                print("解析失败 %s:" % code, status, body)
                sys.exit(1)
            meta_papers[code] = {
                "title": paper["title"],
                "source": paper["source"],
                "path": paper["path"],
                "sha256": paper["actualHash"],
                "paperId": paper_id,
                "chunkCount": body.get("chunkCount"),
            }
            print("已解析 %s: %s 片\n" % (code, body.get("chunkCount")))

            paper_questions = [q for q in questions if q["paper"] == code]
            paper_negatives = [q for q in negatives if q["paper"] == code]
            all_results.extend(
                evaluate_questions(paper_id, paper_questions, paper["pageTexts"])
            )
            paper_overview = [q for q in overview_questions if q["paper"] == code]
            all_overview_results.extend(
                evaluate_questions(paper_id, paper_overview, paper["pageTexts"])
            )
            all_negatives.extend(evaluate_negatives(paper_id, paper_negatives))
    finally:
        for code, paper_id in paper_ids.items():
            delete_paper(paper_id)
            print("已清理测试论文 %s: %s" % (code, paper_id))

    meta = {
        "baseUrl": BASE_URL,
        "gitCommit": git_commit(),
        "label": args.label,
        "papers": meta_papers,
    }
    if args.beta85:
        json_path, md_path = write_beta85_outputs(
            all_overview_results, all_results, all_negatives, meta, args.out
        )
        overview_auto = sum(1 for r in all_overview_results if r["autoHit"])
        alpha_auto = sum(1 for r in all_results if r["autoHit"])
        negative_passed = sum(1 for r in all_negatives if r["passed"])
        print("#85 自动校验：概览 %d/%d（要求 ≥4/5），Alpha %d/%d（要求 ≥9/10），未涉及 %d/%d（要求全通过）"
              % (overview_auto, len(all_overview_results), alpha_auto,
                 len(all_results), negative_passed, len(all_negatives)))
        print("结果已写入：", json_path, md_path)
        if (overview_auto < 4 or alpha_auto < 9
                or negative_passed != len(all_negatives)):
            print("自动校验未达线；检查逐题记录。")
            sys.exit(1)
        print("自动校验达到门槛；仍需人工核对答案是否编造后确认最终命中。")
        sys.exit(2)

    json_path, md_path = write_outputs(all_results, all_negatives, meta, args.out)

    auto_hits = sum(1 for r in all_results if r["autoHit"])
    negative_passed = sum(1 for r in all_negatives if r["passed"])
    print("\n自动命中（不含编造判断）: %d / %d" % (auto_hits, len(all_results)))
    print("未涉及通过: %d / %d" % (negative_passed, len(all_negatives)))
    print("结果已写入:")
    print(" ", json_path)
    print(" ", md_path)
    print("\n请人工补充「答案是否编造」与最终命中结论。")
    sys.exit(0 if auto_hits >= 7 and negative_passed == len(all_negatives) else 1)


if __name__ == "__main__":
    main()
