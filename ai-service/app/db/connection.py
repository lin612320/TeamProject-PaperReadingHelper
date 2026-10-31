"""建立数据库连接
注意：统一从 .env 读连接串。
"""

import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://papermind:papermind_dev@localhost:5432/papermind",
)

def get_connection():
    """返回一个新的数据库连接。"""
    return psycopg.connect(DATABASE_URL)
