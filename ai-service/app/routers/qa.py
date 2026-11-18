"""问答接口（#19）"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db.connection import get_connection
from app.services.RAG import QaError, answer_question

router = APIRouter()

class AskRequest(BaseModel):
    paperId: int
    question: str
    topK: int = 3
    maxCitations: int = 3
    # 前端提供API Key，为空时再使用本地 .env 的配置
    apiKey: str | None = None
    baseUrl: str | None = None
    model: str | None = None

@router.post("/internal/qa/ask")
def ask(body: AskRequest):
    question = body.question.strip()
    if question == "" or len(question) > 500:
        return JSONResponse(
            status_code=422,
            content={"code": "EMPTY_QUESTION", "message": "问题不能为空且不超过 500 字", "detail": None},
        )

    # 契约点：论文不存在 404，尚未解析完成 409
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from papers where id = %s", (body.paperId,))
            if cur.fetchone() is None:
                return JSONResponse(
                    status_code=404,
                    content={"code": "PAPER_NOT_FOUND", "message": "论文不存在", "detail": None},
                )

            cur.execute("select 1 from chunks where paper_id = %s limit 1", (body.paperId,))
            if cur.fetchone() is None:
                return JSONResponse(
                    status_code=409,
                    content={"code": "PAPER_NOT_READY", "message": "论文尚未解析完成", "detail": None},
                )

    # 契约范围：topK 1~8，maxCitations 0~5
    top_k = min(max(body.topK, 1), 8)
    max_citations = min(max(body.maxCitations, 0), 5)

    try:
        result = answer_question(
            body.paperId,
            question,
            top_k,
            max_citations,
            api_key=body.apiKey,
            base_url=body.baseUrl,
            model=body.model,
        )
    except QaError as e:
        if e.code == "PAPER_NOT_FOUND":
            status = 404
        elif e.code == "PAPER_NOT_READY":
            status = 409
        elif e.code == "EMPTY_QUESTION":
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

    return result
