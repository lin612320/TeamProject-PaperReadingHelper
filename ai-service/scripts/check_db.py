# 一次性连接测试：读 -> 写 -> 查回 -> 清理
import os

import psycopg
from dotenv import load_dotenv

load_dotenv()                      # 读 ai-service/.env

url = os.getenv("DATABASE_URL")
conn = psycopg.connect(url)
print("数据库连接成功")

# 1. 先读一下，确认能查
cur = conn.execute("select count(*) from chunks")
print("chunks 当前条数:", cur.fetchone()[0])

# 2. 写：先插 papers，因为 chunks 有外键依赖它
cur = conn.execute(
    "insert into papers (title, filename, file_path) values (%s, %s, %s) returning id",
    ("__test__", "t.pdf", "/tmp/t.pdf"),
)
paper_id = cur.fetchone()[0]       # 拿数据库生成的 id，不要写死
print("新建论文 id:", paper_id)

# 3. 写：插一条 chunk，带一个假的 1024 维向量
#    向量要转成 '[0.01,0.01,...]' 这种字符串，再 ::vector 转换
fake_vector = "[" + ",".join(["0.01"] * 1024) + "]"
conn.execute(
    "insert into chunks (paper_id, chunk_index, page, content, embedding) "
    "values (%s, %s, %s, %s, %s::vector)",
    (paper_id, 0, 1, "这是一条测试片段", fake_vector),
)
conn.commit()                      # psycopg 默认不自动提交，必须 commit
print("插入成功")

# 4. 查回来
cur = conn.execute("select count(*) from chunks where paper_id = %s", (paper_id,))
print("写入后 chunks:", cur.fetchone()[0])

# 5. 清理：删论文，chunks 会被级联删掉
conn.execute("delete from papers where id = %s", (paper_id,))
conn.commit()

cur = conn.execute("select count(*) from chunks where paper_id = %s", (paper_id,))
print("清理后 chunks:", cur.fetchone()[0])

conn.close()
