"""论文问答：检索 → Prompt → 大模型 → 答案与引用（#19）。"""

import os
import time

from app.db.chunks import vector_to_string
from app.db.connection import get_connection
from app.services import llm_client
from app.services.embedder import embed_texts

NO_ANSWER = "本文未涉及该内容"
MAX_TOTAL_SECONDS = 24          # 契约上限 25 秒，留 1 秒余量

# #84 概览类问题：放宽召回，并保证摘要/首段/末段进入上下文
OVERVIEW_TOP_K = 8
OVERVIEW_ANCHOR_LIMIT = 2

OVERVIEW_ZH_PATTERNS = (
    "讲了什么", "讲了啥", "讲的是什么", "主要讲", "主要内容", "概括",
    "总结", "概述", "简介", "贡献", "创新点", "解决什么问题",
    "解决了什么", "解决的问题", "研究问题", "用了什么数据",
    "什么数据集", "结论",
)

OVERVIEW_EN_PATTERNS = (
    "what is this paper about", "what's this paper about",
    "what is the paper about", "what does this paper",
    "what is it about", "main contribution", "contributions",
    "summarize", "summary", "overview", "what problem",
    "what dataset", "conclusion", "key findings",
)

class QaError(Exception):
    """问答链路异常。

    契约:
        code 使用内部错误码，路由层据此返回 HTTP 状态码。
    """

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message

def _reading_order_expr(cur):
    """契约 1.3.0 的 reading_order 由 P6 加列；缺列时返回 NULL，避免整条 SQL 失败。"""
    cur.execute(
        "select 1 from information_schema.columns "
        "where table_name = 'chunks' and column_name = 'reading_order'"
    )
    return "reading_order" if cur.fetchone() is not None else "NULL::int"


def _row_to_chunk(row):
    return {
        "chunk_id": row[0],
        "chunk_index": row[1],
        "page": row[2],
        "content": row[3],
        "bbox_x0": row[4],
        "bbox_y0": row[5],
        "bbox_x1": row[6],
        "bbox_y1": row[7],
        "bbox_mode": row[8],
        "reading_order": row[9],
        "similarity": float(row[10]),
    }


def search_chunks(paper_id, question, top_k=3):
    """把问题转向量，在该论文的 chunks 里取最相关的 top_k 段。"""
    try:
        vectors = embed_texts([question], show_progress_bar=False)
    except Exception as e:
        raise QaError("EMBEDDING_FAILED", "问题向量化失败: " + str(e))

    query_vector = vector_to_string(vectors[0])
    with get_connection() as conn:
        with conn.cursor() as cur:
            order_expr = _reading_order_expr(cur)
            cur.execute(
                "select id, chunk_index, page, content, "
                "bbox_x0, bbox_y0, bbox_x1, bbox_y1, bbox_mode, "
                + order_expr + " as reading_order, "
                "1 - (embedding <=> %s::vector) as similarity "
                "from chunks where paper_id = %s "
                "order by embedding <=> %s::vector limit %s",
                (query_vector, paper_id, query_vector, top_k),
            )
            rows = cur.fetchall()

    return [_row_to_chunk(row) for row in rows]


def is_overview_question(question):
    """判断是不是“讲了什么/贡献/数据/结论”这类概览题。"""
    text = (question or "").strip().lower().replace("’", "'")
    if text == "":
        return False
    if any(pattern in text for pattern in OVERVIEW_ZH_PATTERNS):
        return True
    return any(pattern in text for pattern in OVERVIEW_EN_PATTERNS)


def _fetch_anchor_chunks(paper_id, limit=OVERVIEW_ANCHOR_LIMIT):
    """取首段、摘要附近段、末段，作为概览题的固定上下文。"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            order_expr = _reading_order_expr(cur)
            base = (
                "select id, chunk_index, page, content, "
                "bbox_x0, bbox_y0, bbox_x1, bbox_y1, bbox_mode, "
                + order_expr + " as reading_order, 0.0 as similarity "
                "from chunks where paper_id = %s "
            )

            cur.execute(base + "order by chunk_index asc limit %s",
                        (paper_id, limit))
            first = [_row_to_chunk(row) for row in cur.fetchall()]

            cur.execute(base + "order by chunk_index desc limit %s",
                        (paper_id, limit))
            last = [_row_to_chunk(row) for row in reversed(cur.fetchall())]

            cur.execute(
                base + "and (content ilike %s or content ilike %s) "
                "order by chunk_index asc limit %s",
                (paper_id, "%abstract%", "%摘要%", limit),
            )
            abstract = [_row_to_chunk(row) for row in cur.fetchall()]

    return first, abstract, last


def search_overview_chunks(paper_id, question, top_k=OVERVIEW_TOP_K):
    """概览题：dense top_k + 首段/摘要/末段，去重后优先保留固定上下文。"""
    dense = search_chunks(paper_id, question, top_k)
    first, abstract, last = _fetch_anchor_chunks(paper_id)

    merged = []
    seen = set()
    for chunk in first + abstract + last + dense:
        chunk_id = chunk["chunk_id"]
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        merged.append(chunk)
        if len(merged) >= top_k:
            break
    return merged


def build_prompt(question, chunks, overview=False):
    """把检索片段和问题拼成 Prompt。"""
    parts = []
    for i in range(len(chunks)):
        chunk = chunks[i]
        parts.append("[片段%d｜第%d页]\n%s" % (i + 1, chunk["page"], chunk["content"]))

    if overview:
        system = (
            "你是严谨的论文阅读助手。用户问的是论文的整体内容。"
            "请综合给出的摘要、首段、末段和相关片段，用中文概括："
            "1) 论文主题和要解决的问题；2) 主要贡献或方法；"
            "3) 使用的数据或实验；4) 结论。"
            "只依据原文，不要使用原文之外的知识，不要编造或推测。"
            "如果片段不足以回答，仍然只输出这一句话，不要补充解释：本文未涉及该内容\n"
            "回答使用中文，简洁准确。"
        )
    else:
        system = (
            "你是严谨的论文阅读助手。只依据以下原文作答，不要使用原文之外的知识，"
            "也不要编造或推测。\n"
            "回答前先判断：原文片段是否直接包含回答问题所需的信息。"
            "如果只是字面相关、但没有给出答案，同样算未涉及。\n"
            "未涉及时只输出这一句话，不要补充解释：本文未涉及该内容\n"
            "回答使用中文，简洁准确。"
        )

    user = "原文片段：\n" + "\n\n".join(parts) + "\n\n用户问题：" + question
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

def _build_citations(chunks, max_citations):
    citations = []
    for chunk in chunks[:max_citations]:
        snippet = chunk["content"].strip()
        if len(snippet) > 200:
            snippet = snippet[:200]
        citations.append({
            "page": chunk["page"],
            "snippet": snippet,
            "chunkId": chunk["chunk_id"],
            # #40：返回切片时写入的归一化 bbox 与精度模式；旧数据可为 null
            "bboxX0": chunk.get("bbox_x0"),
            "bboxY0": chunk.get("bbox_y0"),
            "bboxX1": chunk.get("bbox_x1"),
            "bboxY1": chunk.get("bbox_y1"),
            "bboxMode": chunk.get("bbox_mode"),
            # 契约 1.3.0：引用所在 chunk 的页内阅读顺序，老数据可为 null
            "readingOrder": chunk.get("reading_order"),
        })
    return citations

def _token_usage(usage):
    prompt = int(usage.get("prompt_tokens") or 0)
    completion = int(usage.get("completion_tokens") or 0)
    total = int(usage.get("total_tokens") or (prompt + completion))
    cost = (prompt * 0.001 + completion * 0.002) / 1000
    return {
        "prompt": prompt,
        "completion": completion,
        "total": total,
        "costCny": round(cost, 6),
    }

def _result(answer, citations, start, usage=None, model=None):
    if usage is None:
        usage = {}
    return {
        "answer": answer,
        "citations": citations,
        "elapsedMs": int((time.time() - start) * 1000),
        "model": llm_client.model_name(model),
        "tokenUsage": _token_usage(usage),
    }

def answer_question(paper_id, question, top_k=3, max_citations=3,
                    api_key=None, base_url=None, model=None):
    """完整问答链路。调用前由路由层确认论文存在且已有 chunks。

    概览类问题（#84）会放宽到 OVERVIEW_TOP_K，并固定纳入首段/摘要/末段；
    普通问题仍走原来的 top_k + 相似度阈值。
    api_key / base_url / model 由前端设置页按次传入；为空时回退到 .env。
    """
    start = time.time()

    overview = is_overview_question(question)
    if overview:
        chunks = search_overview_chunks(paper_id, question, OVERVIEW_TOP_K)
    else:
        chunks = search_chunks(paper_id, question, top_k)

    if len(chunks) == 0:
        return _result(NO_ANSWER, [], start, model=model)

    if not overview:
        # 仅作兜底下限：bge-m3 的相似度整体偏高（同论文内常见 0.5 左右），
        # “是否真的涉及”主要靠 Prompt 约束，不能只依赖这个阈值。
        # 概览题不套这个门：它问的是论文本身，片段里通常有摘要/首末段。
        min_similarity = float(os.getenv("QA_MIN_SIMILARITY", "0.35"))
        if chunks[0]["similarity"] < min_similarity:
            return _result(NO_ANSWER, [], start, model=model)

    remaining = MAX_TOTAL_SECONDS - (time.time() - start)
    if remaining <= 1:
        # 错误码受 frozen 契约约束仍用 LLM_TIMEOUT，但文案要说明慢在检索
        raise QaError("LLM_TIMEOUT", "检索阶段耗时超过预算")

    messages = build_prompt(question, chunks, overview=overview)
    try:
        answer, usage = llm_client.chat(
            messages,
            timeout=min(remaining, llm_client.DEFAULT_TIMEOUT),
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
    except llm_client.LLMTimeout:
        raise QaError("LLM_TIMEOUT", "大模型请求超时")
    except llm_client.LLMAuthError as e:
        raise QaError("LLM_AUTH_ERROR", "大模型鉴权失败: " + str(e))
    except Exception as e:
        raise QaError("LLM_ERROR", "大模型调用失败: " + str(e))

    answer = answer.strip()
    if NO_ANSWER in answer:
        citations = []
    else:
        citations = _build_citations(chunks, max_citations)

    return _result(answer, citations, start, usage, model=model)
