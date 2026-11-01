"""论文相关接口（解析、删除）"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db.connection import get_connection
from app.services.ingest import IngestError, ingest_paper

router = APIRouter()

class ParseRequest(BaseModel):
    paperId: int
    filePath: str
    force: bool = False

def error_body(code, message):
    return {"code": code, "message": message, "detail": None}

@router.post("/internal/papers/parse")
def parse_paper(body: ParseRequest):
    # 先确认论文存在（契约要求）
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("select 1 from papers where id = %s", (body.paperId,))
            exists = cur.fetchone() is not None

    if not exists:
        return JSONResponse(
            status_code = 404,
            content = error_body("PAPER_NOT_FOUND", "论文不存在"),
        )

    try:
        result = ingest_paper(body.paperId, body.filePath)
    except IngestError as e:
        if e.code in ("FILE_NOT_FOUND", "NOT_PDF"):
            status = 400
        else:
            status = 500
        return JSONResponse(
            status_code=status,
            content=error_body(e.code, e.message),
        )

    return result

@router.delete("/internal/papers/{paperId}")
def delete_paper_data(paperId: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from chunks where paper_id = %s", (paperId,))
            deleted = cur.rowcount
    return {"paperId": paperId, "deletedChunks": deleted}
