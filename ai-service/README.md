# ai-service · AI / PDF 服务

FastAPI · PyMuPDF · pgvector · DeepSeek（OpenAI 兼容接口）

## 使用前准备（首次 clone 必读）

按下面 5 步做完，即可使用 ai-service 的全部现有功能。

### 1. 环境要求

| 依赖 | 要求 |
|---|---|
| Python | 3.10+（团队实测 3.13） |
| Docker Desktop | 用于启动 PostgreSQL + pgvector |
| 磁盘 | 约 5 GB（PyTorch 依赖 + bge-m3 模型） |
| 网络 | 首次解析需访问 HuggingFace 下载模型（约 2.2 GB） |

### 2. 启动数据库（仓库根目录）

```bash
docker compose up -d postgres
docker compose ps          # 等到 healthy
```

表结构由 `docs/03-数据库表结构.sql` 在**数据卷首次创建时**自动导入。
如果之前已经跑过、`pgdata` 卷已存在，需要手动执行一次：

```bash
docker exec -i papermind-postgres psql -U papermind -d papermind < docs/03-数据库表结构.sql
```

### 3. 安装依赖（ai-service 目录）

```bash
cd ai-service
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

依赖包含 PyTorch，首次安装约 2 GB，请耐心等待。国内网络慢可加镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 配置 .env（ai-service 目录）

```bash
cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
```

打开 `ai-service/.env` 填写。**只有 `DATABASE_URL` 是硬性要求；`DEEPSEEK_API_KEY` 只影响问答。**

| 变量 | 是否必填 | 默认值 | 说明 |
|---|---|---|---|
| `DATABASE_URL` | **必填** | `postgresql://papermind:papermind_dev@localhost:5432/papermind` | 与 `docker-compose.yml` 保持一致即可 |
| `DEEPSEEK_API_KEY` | **问答必填** | 空 | 不填：健康检查/解析/检索正常，问答返回 500，message 为「未配置 DEEPSEEK_API_KEY」 |
| `DEEPSEEK_BASE_URL` | 否 | `https://api.deepseek.com` | OpenAI 兼容接口地址 |
| `LLM_MODEL` | 否 | `deepseek-chat` | 问答使用的模型名 |
| `QA_MIN_SIMILARITY` | 否 | `0.35` | 检索相似度低于该值直接返回「本文未涉及该内容」 |

说明：

- `.env` 已在 `.gitignore` 中，**不会提交**。
- 修改 `.env` 后**必须重启服务**才生效（`load_dotenv()` 只在进程启动时读一次）。
- `EMBEDDING_MODEL` / `VECTOR_DIM` 仅用于健康检查展示；实际向量模型固定为 `BAAI/bge-m3`（1024 维），改这两个变量不会切换模型。

### 5. 启动并验证（ai-service 目录）

```bash
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# macOS / Linux:
# .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开一个终端验证：

```bash
curl http://localhost:8000/internal/health
```

期望返回：

```json
{
  "status": "ok",
  "model": "deepseek-chat",
  "embeddingModel": "bge-m3",
  "vectorDim": 1024,
  "dbReady": true,
  "version": "0.1.0"
}
```

`dbReady` 为 `false` 时接口返回 503，说明数据库没连上。

接口文档（FastAPI 自动生成）：<http://localhost:8000/docs>

## 现有功能与使用前提

| 功能 | 接口 | 使用前提 |
|---|---|---|
| 健康检查 | `GET /internal/health` | 数据库可用 |
| 解析入库 | `POST /internal/papers/parse` | ① `papers` 表已存在该 `paperId`；② `filePath` 是本机可读的 PDF 绝对路径；③ 首次调用会下载 bge-m3 |
| 删除切片 | `DELETE /internal/papers/{paperId}` | 数据库可用 |
| 论文问答 | `POST /internal/qa/ask` | ① 论文存在且已有 chunks；② 已配置 `DEEPSEEK_API_KEY` |

注意：

- **解析接口不会自动创建 `papers` 记录**，调用方需先插入一行（正常上传流程由后端完成）。
- 问答接口只读 `chunks`，所以必须先解析成功。
- 默认端口 8000；被占用时用 `--port` 换一个。
- `data/` 目录不随仓库提供。解析使用调用方传入的 PDF 路径，**不需要把文件放进 `data/`**。

单独试接口时，可以先插一条测试论文（`paper_id` 用返回值）：

```bash
docker exec -it papermind-postgres psql -U papermind -d papermind
```

```sql
INSERT INTO papers (title, filename, file_path)
VALUES ('测试论文', 'test.pdf', 'D:/pdfs/test.pdf')
RETURNING id;
```

## 国内网络：加速模型下载

bge-m3 在**首次解析时**下载（不是启动时）。网络慢或失败时，在启动服务的同一个终端先设置镜像，再启动：

```bash
export HF_ENDPOINT=https://hf-mirror.com          # macOS / Linux / Git Bash
$env:HF_ENDPOINT="https://hf-mirror.com"          # Windows PowerShell
```

> 该变量必须在进程启动前设置。写在 `.env` 里不保证生效（HuggingFace 在模块导入时读取）。

## Alpha 范围（只做这些）

| 能力 | Issue | 验收 |
|---|---|---|
| PyMuPDF 文本抽取（blocks 顺序，双栏**先凑合**） | #17 | 段落完整、带页码 |
| 切片 + Embedding 入库 | #18 | 单篇论文可写入 `chunks` 表 |
| 检索 + Prompt + 返回答案与页码 | #19 | 返回答案 + 引用片段 + 页码 |
| 答案质量抽样（10 题） | #20 | 引用页码准确率 ≥ 70% |

## 明确不做（Beta / RC）

双栏阅读流排序算法、bbox 精确定位（Beta 主菜）、跨文献对比 Prompt、重排与成本优化。

## 开发调试（可选，不参与正常使用）

`scripts/` 下是分层自检脚本，用来定位问题，不属于对外接口。多数脚本支持传入 PDF 路径：

```bash
.venv/Scripts/python.exe -m scripts.check_db
.venv/Scripts/python.exe -m scripts.check_rag "D:/pdfs/test.pdf"
.venv/Scripts/python.exe -m scripts.check_qa "D:/pdfs/test.pdf"
```

- `check_rag` 直接调用服务层，验证「检索 → Prompt → 返回结构」；未配置 `DEEPSEEK_API_KEY` 时自动使用 mock 模型，不消耗额度。
- `check_qa` 通过 HTTP 调用 `/internal/qa/ask`，验证 200 响应结构与 404/409/422 错误分支，**需要先启动 uvicorn**。
- `check_embedder.py` 目前固定读取 `data/attention.pdf`，需要自行放一份样本。
- 这些脚本会临时插入测试数据并在结束时清理，不影响正常数据。

## 约定

- 输入输出严格按 `docs/02-内部服务契约.yaml`，`bbox*` 字段 Alpha 一律返回 `null`
- 切片建议 500–800 字、重叠 100 字，chunk 必须带 `page`（1 起）
- 答案必须基于检索到的段落，无依据时明确说「本文未涉及」，**不许编造**
- token 用量与费用按 `(prompt_tokens*0.001 + completion_tokens*0.002)/1000` 记录，写日志
- 单次问答服务端耗时目标 < 20s，超时返回结构化错误而非挂死

## 目录约定

```
app/
├─ main.py          FastAPI 入口
├─ routers/         路由（paper / qa）
├─ services/        pdf_extractor / chunker / embedder / ingest / RAG / llm_client
└─ db/              连接与数据库操作
```
