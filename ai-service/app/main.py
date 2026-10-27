import os

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://papermind:papermind_dev@localhost:5432/papermind",
)
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "bge-m3")
VECTOR_DIM = int(os.getenv("VECTOR_DIM", "1024"))

app = FastAPI(title="PaperMind AI Service")


def check_db():
    conn = None
    try:
        conn = psycopg.connect(DATABASE_URL, connect_timeout=3)
        conn.execute("select 1")
        return True
    except Exception:
        return False
    finally:
        if conn is not None:
            conn.close()


@app.get("/internal/health")
def health():
    db_ok = check_db()
    if not db_ok:
        # 契约里 503 表示依赖不可用，P4 据此判断能不能发解析/问答请求
        return JSONResponse(
            status_code=503,
            content={
                "code": "INTERNAL_ERROR",
                "message": "数据库连接失败",
                "detail": None,
            },
        )
    return {
        "status": "ok",
        "model": LLM_MODEL,
        "embeddingModel": EMBEDDING_MODEL,
        "vectorDim": VECTOR_DIM,
        "dbReady": True,
        "version": "0.1.0",
    }
