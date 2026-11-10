"""划词翻译/术语解释接口。"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.db.connection import get_connection
from app.services.explain import ExplainError, MAX_CONTEXT, explain_text
from app.services.llm_config import LlmConfig

router = APIRouter()

class ExplainRequest(BaseModel):
    # paperId 可为空：未入库论文也支持翻译/解释，只是不查库内上下文
    paperId: int | None = None
    text: str
    mode: str = "translate"
    # 前端可从 PDF 当前页截取一段上下文；未传则按 paperId 查库
    context: str | None = None
    # 与问答一致：前端设置页的 Key 按次传入
    apiKey: str | None = None
    baseUrl: str | None = None
    model: str | None = None

def _load_context(paper_id, text, provided_context):
    """返回 (论文标题, 上下文)。

    论文不存在或未入库时返回空，不报错；两种情况都继续翻译/解释。
    优先用前端传的 context；没有时再从 chunks 里找命中片段。
    """
    title = ""
    context = (provided_context or "").strip()

    if paper_id is None:
        return title, context

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("select title from papers where id = %s", (paper_id,))
            row = cur.fetchone()
            if row is None:
                return title, context

            title = row[0] or ""
            if context:
                return title, context

            # 用选中文本前 60 字去 chunks 里找上下文；空白归一化后再匹配
            needle = " ".join((text or "").split())[:60]
            if needle == "":
                return title, context

            cur.execute(
                "select content from chunks where paper_id = %s "
                "and position(lower(%s) in lower("
                "replace(replace(content, E'\\n', ' '), E'\\r', ' '))) > 0 "
                "limit 1",
                (paper_id, needle),
            )
            row = cur.fetchone()
            if row is None:
                return title, context

            normalized = row[0].replace("\r", " ").replace("\n", " ")
            index = normalized.lower().find(needle.lower())
            if index < 0:
                return title, context

            start = max(0, index - 200)
            end = min(len(normalized), index + len(needle) + 200)
            context = normalized[start:end].strip()[:MAX_CONTEXT]

    return title, context

@router.post("/internal/explain")
def explain(body: ExplainRequest):
    title, context = _load_context(body.paperId, body.text, body.context)
    config = LlmConfig.from_request(body.apiKey, body.baseUrl, body.model)

    try:
        return explain_text(
            title, context, body.text, body.mode, config
        )
    except ExplainError as e:
        if e.code in ("INVALID_MODE", "EMPTY_TEXT"):
            status = 422
        elif e.code == "LLM_TIMEOUT":
            status = 504
        elif e.code == "LLM_AUTH_ERROR":
            status = 401
        else:
            status = 500

        return JSONResponse(
            status_code=status,
            content={"code": e.code, "message": e.message, "detail": None},
        )
