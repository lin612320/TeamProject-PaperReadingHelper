"""论文问答：检索 → Prompt → 大模型 → 答案与引用（#19）。"""

import os
import time

from app.db.chunks import vector_to_string
from app.db.connection import get_connection
from app.services import llm_client
from app.services.embedder import embed_texts

NO_ANSWER = "本文未涉及该内容"
MAX_TOTAL_SECONDS = 24          # 契约上限 25 秒，留 1 秒余量

class QaError(Exception):
    """问答链路异常。

    契约:
        code 使用内部错误码，路由层据此返回 HTTP 状态码。
    """

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message

def search_chunks(paper_id, question, top_k=3):
    """把问题转向量，在该论文的 chunks 里取最相关的 top_k 段。"""
    try:
        vectors = embed_texts([question], show_progress_bar=False)
    except Exception as e:
        raise QaError("EMBEDDING_FAILED", "问题向量化失败: " + str(e))

    query_vector = vector_to_string(vectors[0])
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select id, chunk_index, page, content, "
                "1 - (embedding <=> %s::vector) as similarity "
                "from chunks where paper_id = %s "
                "order by embedding <=> %s::vector limit %s",
                (query_vector, paper_id, query_vector, top_k),
            )
            rows = cur.fetchall()

    results = []
    for row in rows:
        results.append({
            "chunk_id": row[0],
            "chunk_index": row[1],
            "page": row[2],
            "content": row[3],
            "similarity": float(row[4]),
        })
    return results

def build_prompt(question, chunks):
    """把检索片段和问题拼成 Prompt。"""
    parts = []
    for i in range(len(chunks)):
        chunk = chunks[i]
        parts.append("[片段%d｜第%d页]\n%s" % (i + 1, chunk["page"], chunk["content"]))

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
            # Alpha 阶段 bbox 一律返回 null
            "bboxX0": None,
            "bboxY0": None,
            "bboxX1": None,
            "bboxY1": None,
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

def _result(answer, citations, start, usage=None):
    if usage is None:
        usage = {}
    return {
        "answer": answer,
        "citations": citations,
        "elapsedMs": int((time.time() - start) * 1000),
        "model": llm_client.model_name(),
        "tokenUsage": _token_usage(usage),
    }

def answer_question(paper_id, question, top_k=3, max_citations=3):
    """完整问答链路。调用前由路由层确认论文存在且已有 chunks。"""
    start = time.time()

    chunks = search_chunks(paper_id, question, top_k)
    if len(chunks) == 0:
        return _result(NO_ANSWER, [], start)

    # 仅作兜底下限：bge-m3 的相似度整体偏高（同论文内常见 0.5 左右），
    # “是否真的涉及”主要靠 Prompt 约束，不能只依赖这个阈值。
    min_similarity = float(os.getenv("QA_MIN_SIMILARITY", "0.35"))
    if chunks[0]["similarity"] < min_similarity:
        return _result(NO_ANSWER, [], start)

    remaining = MAX_TOTAL_SECONDS - (time.time() - start)
    if remaining <= 1:
        # 错误码受 frozen 契约约束仍用 LLM_TIMEOUT，但文案要说明慢在检索
        raise QaError("LLM_TIMEOUT", "检索阶段耗时超过预算")

    messages = build_prompt(question, chunks)
    try:
        answer, usage = llm_client.chat(messages, timeout=min(remaining, llm_client.DEFAULT_TIMEOUT))
    except llm_client.LLMTimeout:
        raise QaError("LLM_TIMEOUT", "大模型请求超时")
    except Exception as e:
        raise QaError("LLM_ERROR", "大模型调用失败: " + str(e))

    answer = answer.strip()
    if NO_ANSWER in answer:
        citations = []
    else:
        citations = _build_citations(chunks, max_citations)

    return _result(answer, citations, start, usage)
