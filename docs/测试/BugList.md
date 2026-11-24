# Bug List（Alpha + Beta）

> P7 李义朋 · [#25](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/25) · **v1.7 · 2026-11-24** · 测试版本 `master`（容器化）
> 版式：概览表（5 列，一屏可读）+ 每条明细分块。
> **状态：26 条 · 已修复 19 · 不修复 1（BUG-012，接受风险）· 待修复 6**（BUG-020 契约待补、BUG-021 契约待升、BUG-022 受 BUG-027 阻塞、BUG-024/025 隔离漏洞、BUG-027 缺列）
> 分区：BUG-001～019 为 Alpha 段；**BUG-020～023 为 Beta 段**（2026-11-18 起，来自 P1 契约对账与用户视角自查）；**BUG-024～027 为 Beta 代码审查项**（2026-11-23 起拉取最新提交后审出）

## 概览

| 编号      | 级别  | 归属        | 状态        | 一句话                                                                   |
| ------- | --- | --------- | --------- | --------------------------------------------------------------------- |
| BUG-001 | S0  | P3        | 已修复       | 上传页没有上传动作                                                             |
| BUG-002 | S1  | P4        | 已修复       | 响应泄露磁盘绝对路径                                                            |
| BUG-003 | S1  | P4        | 已修复       | 上传响应字段不符契约                                                            |
| BUG-004 | S1  | P4        | 已修复       | `.pdf` 后缀 + docx 内容被入库（回归）                                            |
| BUG-005 | S2  | P4        | 已修复       | 超 50MB 返回 5000 而非 1003                                                |
| BUG-006 | S1  | P4        | 已修复       | 页数/切片数写死 15/128                                                       |
| BUG-007 | S1  | P4        | 已修复       | 无访问日志                                                                 |
| BUG-008 | S1  | P4        | 已修复       | 解析失败原因只写 `unknown error`                                              |
| BUG-009 | S2  | P4 + P7   | 已修复       | `.docx` 后缀被接口接受                                                       |
| BUG-010 | S0  | P4        | 已修复       | 解析超时（25s 上限 vs 实际 60s+）                                               |
| BUG-011 | S2  | P4        | 已修复       | 上传时间早 8 小时                                                            |
| BUG-012 | S1  | P6（主）/ P5 | 不修复（接受风险） | 容器无模型，解析必失败（且假健康）                                                     |
| BUG-013 | S1  | P6        | 已修复       | nginx 不认 `.mjs`，阅读页白屏                                                 |
| BUG-015 | S2  | P4        | 已修复       | `file_path` 存绝对路径，换环境读不到                                              |
| BUG-016 | S1  | P4        | 已修复       | `apiKey` 未转发，用户 Key 不生效                                               |
| BUG-017 | S1  | P4        | 已修复       | `/api/search` 降级时缺 `degraded` / `cached` 标记，前端无法区分“没结果”与“网断了”         |
| BUG-018 | S2  | P6        | 已修复 | 检索命中缓存时 `message` 里的更新时间用 UTC，比北京时间慢 8 小时                             |
| BUG-019 | S0  | P6        | 已修复 | `chunks.bbox_mode` 列未创建，`RAG.py` 查询报错 → `/api/qa/ask` 全部 3001，问答主链不可用 |
| BUG-020 | S2  | P4        | 待修复 | `papers` 列表/详情返回字段与契约不一致（缺 3、多 2） |
| BUG-021 | S1  | P4        | 已修代码（契约待升） | 检索超时 10s 与实测 9.19s 冲突，检索必然降级 |
| BUG-022 | S2  | P5        | 已修代码（受 BUG-027 阻塞） | `citations` 缺 `readingOrder`（契约 1.3.0 已冻结） |
| BUG-023 | S2  | P1（契约）  | 已修复 | `bboxMode` 按版面类型定值，与 B03 验收互斥（文档矛盾） |
| BUG-024 | S1  | P4        | 待修复 | `/api/explain` 不校验论文归属，跨用户读到他人标题与正文片段 |
| BUG-025 | S1  | P6        | 待修复 | `ai-service:8000` 对外发布且 `/internal/*` 无鉴权，绕过 backend 校验 |
| BUG-026 | S2  | P4        | 已修复 | `UserContext` 未设置时静默回退 user 1，开 enforce 后变越权 |
| BUG-027 | S1  | P6        | 待修复 | `chunks.reading_order` 无建列语句，#81 写入永不落库 |

**统计**：26 条 · 已修复 19 · 不修复 1（BUG-012，接受风险）· 待修复 6

级别：**S0** 主链断（演示走不通）· **S1** 验收不达标 · **S2** 体验或契约一致性
（S = Severity，与分工编号 P1–P7 区分；归属列的 P3/P4 才是人）

状态：待修复 / 已修复 / **不修复（接受风险）**。（不修复 = 例会已决定承担该风险，需写明前提与后果；原「待确定」的 BUG-015 经组长核实属实，已转「待修复」并已复测通过）

---

## 明细

### BUG-001 · 上传页没有上传动作（S0 · P3 · 已修复）

- **版本**：`8ecb98c`
- **现象**：选完 PDF 只显示绿字「文件格式正确」，没有上传按钮，也不发请求。
- **复现**：选 `demo-10p.pdf` → 看页面 + F12 Network。
- **影响**：演示第 2 步走不通；F1-01 界面层无法验证。

---

### BUG-002 · 响应泄露磁盘绝对路径（S1 · P4 · 已修复）

- **版本**：`8ecb98c`
- **现象**：上传响应带出 `data.path`（服务器盘符路径）。
- **复现**：`curl -X POST /api/papers -F "file=@demo-10p.pdf"`。
- **影响**：泄露目录结构；违反建表 SQL「禁止对外暴露」。

---

### BUG-003 · 上传响应字段不符契约（S1 · P4 · 已修复）

- **版本**：`8ecb98c`
- **现象**：`POST /api/papers` 响应缺 `pageCount`、`createdAt`，多 `size`、`path`（列表接口字段正确，仅上传接口不符）。
- **复现**：上传任意 PDF 后看响应体，对照契约 `PaperDetail`。
- **影响**：前端按契约取值会拿到 `undefined`。

---

### BUG-004 · `.pdf` 后缀 + docx 内容被入库（回归）（S1 · P4 · 已修复）

- **版本**：`8ecb98c`／复现于 `410ed69`，修复于 `03ca4b8`
- **现象**：`upload()` 只做后缀校验，已有的 `isPdf()` 定义后未被调用；`03ca4b8` 恢复文件头校验后已修。
- **复现**：上传 `2026数据结构基础实验.pdf`（前 8 字节 `50 4B 03 04` 即 `PK`）→ 修复前 200 入库；**修复后复测 400 / `1002`**，正常 PDF 仍 200。
- **影响**：脏数据入库；该文件必然解析失败；F1-04 曾由通过回退为不通过。

---

### BUG-005 · 超 50MB 返回 5000 而非 1003（S2 · P4 · 已修复）

- **版本**：`8ecb98c`
- **现象**：上传 51MB PDF 返回 `5000 服务器内部错误`，而非契约规定的 `1003 文件超过 50MB`。
- **复现**：`curl -i -X POST /api/papers -F "file=@big.pdf"`。对照：同内容的 48MB 文件返回 `code=0`，证明与内容无关，只取决于大小。
- **影响**：无法区分「文件太大」和「服务崩了」，用户不知道该改什么。

---

### BUG-006 · 页数/切片数写死 15/128（S1 · P4 · 已修复）

- **版本**：`8ecb98c`
- **现象**：解析完成后 `pageCount` 恒为 15、`chunkCount` 恒为 128，与文件无关。
- **复现**：上传 10 页的 `demo-10p.pdf`，4 秒后 `GET /api/papers/4`，返回 `pageCount:15`、`chunkCount:128`。
- **影响**：列表页数全部错误；F1「10 页 PDF」验收无法证明；切片数失真。

---

### BUG-007 · 无访问日志（S1 · P4 · 已修复）

- **版本**：`8ecb98c`
- **现象**：发请求后控制台只有启动日志和首次请求的懒加载初始化，没有路径、文件名、状态码。
- **复现**：启动后上传任意 PDF，翻控制台日志，找不到这次请求的任何记录。
- **影响**：出问题无法定位请求/文件/错误；`#23`「运行日志可查」不达标。

---

### BUG-008 · 解析失败原因只写 `unknown error`（S1 · P4 · 已修复）

- **版本**：`7d39ee8`
- **现象**：`parseError` 只有 `unknown error`，看不出是连不上 AI 还是超时；`410ed69` 起按异常类型分别写入「连接超时 / 解析超时：AI 服务未在 N 秒内响应 / 连接被拒」。
- **复现**：停掉 AI 服务（8000 无监听）后上传任意 PDF，`GET /api/papers/{id}` → 修复前 `parseError:"unknown error"`，修复后为可读中文原因。
- **影响**：用户与测试无法定位故障；`#13` 失败路径不可观测。

---

### BUG-009 · `.docx` 后缀被接口接受（S2 · P4 + P7 · 已修复）

- **版本**：`7d39ee8`
- **现象**：后缀 `.docx`、内容却是合法 PDF 的文件被接受并入库（HTTP 200，`id=6`）；`410ed69` 起按后缀校验，非 `.pdf` 一律拒。
- **复现**：`curl -F "file=@not-a-pdf.docx" /api/papers` → 修复前 200；修复后 400 / `1002`。
- **影响**：前端按后缀拦、接口按内容放行，两层不一致；口径已定：**接口按后缀拒**（与 F1-02 判据一致）。

---

### BUG-010 · 解析超时（25s 上限 vs 实际 60s+）（S0 · P4 · 已修复）

- **版本**：`7d39ee8`
- **现象**：上传后解析必然失败，`parseError=request timed out`、`chunkCount=0`，文献不可提问（DB `created_at`→`updated_at` 实测 **25.0 秒**）。
- **复现**：上传 20 页中文论文（1.88 MB），轮询 `GET /api/papers/{id}` 直至 `failed`。
- **影响**：同一文件 AI 直连解析需 60 秒以上（65 片），后端上限 25 秒（`ParseService.java:64`）→ 必然超时；F1-10 与 F3 正例全部不可测。`410ed69` 起超时可配（默认 180 秒），复测通过。
- **说明**：本条曾与「无头浏览器渲染卡住」混淆，后者经真机复核为误判并撤回，编号腾出后用于本条。

---

### BUG-011 · 上传时间早 8 小时（S2 · P4 · 已修复）

- **版本**：`master`（容器化）
- **现象**：后端 `to_char(created_at, ...)`（`PaperController.java:60`／`:194`）按**数据库会话时区**渲染，容器 JVM 为 UTC，故渲染成 UTC 且**返回字符串不带时区偏移**，前端只能原样显示。
- **复现**：容器化启动后上传任意 PDF。DB `created_at` 为 `2026-11-06 16:05:58+08`（存得对），接口返回 `2026-11-06T08:05:58`；同一行 `session=UTC` 下渲染即 08:05:58；`backend` 容器 `date` 为 UTC、`postgres` 为 CST。
- **影响**：列表时间全部偏差 8 小时；跨时区部署更混乱。
- **修法**：`to_char(created_at AT TIME ZONE 'Asia/Shanghai', ...)` 或返回带 `Z` 的完整 ISO 交前端转换；**禁止前端硬加 8 小时**。
- **复测**：`PaperController.java:36` 已改为 `to_char(created_at AT TIME ZONE 'Asia/Shanghai', ...)`；接口返回与库内时间一致、带时区语义，2026-11-07 复测通过。

---

### BUG-012 · 容器无模型，解析必失败（且假健康）（S1 · P6（主）/ P5 · 不修复）

- **版本**：`master`（容器化）
- **现象**：`EMBEDDING_FAILED — couldn't connect to hf-mirror.com ... not in cached files`。成因：`ai-service/Dockerfile` 无模型预下载 + `hf-cache` 命名卷新建为空 + `embedder.py:15` 先试本地缓存、`:18` 回落联网。
- **复现**：`docker compose up -d` 后上传 PDF，`GET /api/papers/{id}` → `failed`；`docker compose exec ai-service ls /root/.cache/huggingface` 为空；本机能跑只因卷里已有 4.3G 模型。
- **影响**：主链断在解析，演示第 3 步之后不可用。
- **附加风险**：`main.py:32` 预热失败不阻塞启动，容器恒定显示 healthy 而模型不可用——**`docker compose ps` 全绿不代表能用**；需给 `/internal/health` 增加 `model_ready` 字段并以其判 healthcheck。
- **处置（D13 站会，2026-11-08）**：**接受风险、不修**。理由：答辩与测试统一使用 P1 笔记本，其 `hf-cache` 卷内已含 4.3 GB 模型。
- **前提（必须遵守）**：**不清卷、不换目录**——compose 项目名随目录变化会新建空卷，届时模型又会缺失；`docker compose down -v` 同样会删卷。
- **后果**：干净环境（新机器 / 新目录 / 清卷后）首次上传必失败；换机演示前需先拷模型或预热。

---

### BUG-013 · nginx 不认 `.mjs`，阅读页白屏（S1 · P6 · 已修复）

- **版本**：`master`（容器化）
- **现象**：`pdf_worker_min-*.mjs` 被 nginx 以 `application/octet-stream` 返回，浏览器按 ES 模块规范拒绝执行，pdf.js 降级 fake worker 后渲染失败。nginx 1.31.8 的 `mime.types` 只有 `js`、没有 `mjs`，落到 `default_type`。
- **复现**：容器起全栈后打开任意论文阅读页；`curl -I http://localhost:8081/assets/pdf.worker.min-*.mjs` → `200 / application/octet-stream`；F12 Console 报 `Expected a JavaScript module script but the server responded with a MIME type of "application/octet-stream"`；同一 id 的 `/file` 接口返回 200 / `application/pdf`。
- **影响**：容器环境阅读链路整体不可用（F2 组不可演示）；前端提示误报「无法连接到服务器」（文案问题并入本条）。
- **修法**：`frontend/nginx.conf` 加 `include mime.types` + `types { application/javascript mjs; }`，**前端代码零改动**（`50fa38e`，合并提交 `e451dd9`）。
- **复测（2026-11-08）**：`frontend/nginx.conf` 已含 `mjs`；8081 打开论文阅读页正常渲染，Console 无 `non-JavaScript MIME type` 报错。

---

### BUG-015 · `file_path` 存绝对路径，换环境读不到（S2 · P4 · 已修复）

- **版本**：`master`（容器化）
- **现象**：`papers.file_path` 存的是绝对路径（`PaperController.java:174` 写入 `target.getAbsolutePath()`），切换运行方式后旧记录文件不可读：宿主机为 `C:\...\backend\uploads\...`，容器内为 `/app/uploads/...`。
- **复现**：手工运行后端时上传若干论文 → 切到容器运行（共用同一 postgres 卷）→ 点开这些论文报「打不开这份文献」。
- **影响**：同一数据库切换运行环境后旧数据不可用。
- **修法**：只存文件名 `savedName`，读取时 `Paths.get(uploadDir, savedName)`；老数据迁移 `UPDATE papers SET file_path = regexp_replace(file_path, '^.*[\\/]', '');`。
- **复测**：`PaperController.java:173` 入库改写 `savedName`，读取走 `resolveFile()`；新上传记录为文件名形式、`/file` 返回 200，2026-11-07 复测通过。旧记录需跑迁移 SQL。

---

### BUG-016 · `apiKey` 未转发，用户 Key 不生效（S1 · P4 · 已修复）

- **版本**：`master`（本地 + 容器）
- **现象**：`QaController.java:79-82` 组装转发请求时只带 `paperId/question/topK/maxCitations`，把 `apiKey` / `baseUrl` / `model` 丢了，实际用的是服务端 `.env`。
- **复现**：传假 Key 仍正常作答：`-d '{"paperId":13,"question":"…","apiKey":"sk-fake"}'` → 修复前 HTTP 200；**修复后应为 400 / `3003 AI_SERVICE_AUTH_ERROR`**，`message` 能看出是 Key 问题。
- **影响**：用户自己填的 Key 永远不生效，会认为功能是假的；契约 1.0.2 已定义该字段。
- **验收**：假 Key → 400/3003；真 Key 生效；密钥不落库/不写日志/不回显；不传 Key 走 `.env` 兜底；前端提示「API Key 无效，请到设置页检查」，不得显示成网络错误或解析中。
- **复测（2026-11-07）**：假 Key `sk-fake` → `HTTP 400` + `{"code":3003,"message":"API Key 无效，请到设置页检查"}`；真 Key 正常作答；`QaController.java:84-86` 已 `putIfPresent` 三个字段；`ErrorCode.java:15` 已定义 3003（http 400）。

---

### BUG-017 · `/api/search` 降级时缺 `degraded` / `cached` 标记（S1 · P4 · 已修复）

- **发现**：2026-11-10 · P7 李义朋 · F5-06（断网降级）实测
- **现象**：断网后 `GET /api/search?keyword=attention&source=arxiv` 返回 `HTTP 200`、`{"code":0,"data":{"total":0,"items":[]}}`，**无 `degraded` 字段**。
- **契约要求**（`01-api-contract.yaml` 1.1.0，第 166–169 行）：
  - 外部请求超时 → 返回已拿到结果 + `data.degraded=true`，不得 500
  - 无结果且外部不可达 → 空列表 + `data.degraded=true`
  - 命中 Redis 缓存 → `data.cached=true`
- **根因**：`SearchController.java:57-64` 的两个 catch 分支只塞了 `total=0`、`items=[]`，未写 `degraded`；`cached` 字段全文件不存在（缓存属 #43，未交付）。
- **影响**：前端无法区分「该关键词确实没结果」与「网络不可达/上游超时」，只能统一提示“没找到”，用户会误以为搜错了词；也无法提示“已使用缓存”。
- **修法**：两个 catch 分支加 `data.put("degraded", true)`；成功路径加 `data.put("degraded", false)`；#43 交付后补 `cached`。
- **关联用例**：F5-06（已通过）、F5-07（已通过）
- **修复**：`8dd04db`（11-10 13:05，P4）检索降级返回 `degraded`/`cached` 标记，arXiv 连接超时重试一次。
- **复测（2026-11-11）**：清空 Redis 缓存 + 断网 + 未搜过的关键词 `quantum error correction survey` → `HTTP 200`、0.04s、`{"total":0,"items":[],"degraded":true,"cached":false,"message":"外部数据源不可用"}`；不 500、不挂起，通过。

---

### BUG-018 · 检索缓存提示时间为 UTC，比北京时间慢 8 小时（S2 · P6 · 已修复）

- **发现**：2026-11-11 · P7 李义朋 · F5-07（检索缓存）实测
- **现象**：第二次搜索命中缓存，返回 `message": "离线缓存（更新时间 2026-11-11 08:02:43）"`，而实测时刻为北京时间 **16:02**，正好差 8 小时。
- **根因**：`SearchController.writeCache()` 用 `LocalDateTime.now()` 取 JVM 默认时区，容器内为 UTC；与 BUG-011（上传时间差 8 小时）同类。
- **影响**：用户看到“更新于 08:02”，会误以为缓存是 8 小时前的旧数据，从而反复刷新，抵消缓存的意义。
- **修法**：改用 `LocalDateTime.now(ZoneId.of("Asia/Shanghai"))`，或统一在容器注入 `TZ=Asia/Shanghai`。
- **修复**：`510a874`（11-11 11:53，P4）缓存时间改用 `ZonedDateTime.now(ZoneId.of("Asia/Shanghai"))`，提示从 `data.message` 移到**顶层 `message`**，缓存 key 按分页隔离。
- **复测（2026-11-12）**：搜两次同词，第二次顶层 `message` = 「离线缓存（更新时间 2026-11-12 18:58:18）」，与本机时间 18:58:18 **偏差 0 分钟**；`cached=true`、`degraded=false`，通过。
- **关联用例**：F5-07

---

### BUG-019 · `chunks.bbox_mode` 列未创建，问答全部 3001（S0 · P6 · 已修复）

- **发现**：2026-11-11 · P7 李义朋 · F6-01 实测（对 paperId=54 提问）
- **现象**：`POST /api/qa/ask` 返回 `{"code":3001,"message":"AI 服务调用失败","data":null}`；ai-service 日志：
  `psycopg.errors.UndefinedColumn: column "bbox_mode" does not exist`，SQL 中含 `SELECT ... bbox_x0, bbox_y0, bbox_x1, bbox_y1, bbox_mode, ...`。
- **根因**：`docs/契约/03-数据库表结构.sql` 第 110 行定义了 `bbox_mode TEXT CHECK (bbox_mode IN ('precise','block'))`，但存量库迁移语句在第 133 行是**注释状态**，未执行；实际 `chunks` 表只有 13 列，无 `bbox_mode`。
- **为什么没早发现**：写入侧 `ai-service/app/db/chunks.py` 有 `_has_bbox_mode_column()` 兜底（列不存在时只写 bbox_*），因此**解析一直正常**；读取侧 `RAG.py:38` 无兜底，一旦提问即整条 SQL 报错。
- **影响**：**问答主链路完全不可用**（所有论文、所有问题均 3001），且前端只显示“AI 服务调用失败”，难以定位。
- **修法**：执行迁移 `ALTER TABLE chunks ADD COLUMN IF NOT EXISTS bbox_mode TEXT CHECK (bbox_mode IN ('precise','block'));`；并把 `docs/03` 中的迁移语句从注释改为正式部署步骤，启动自检增加列检查。
- **关联用例**：F6-01/02/03/05（全部测不了）、F5-10（复测受影响）
- **修复**：`e7b8203`（11-11 12:22，P6）将 `docs/03:133` 的迁移语句从注释转正；测试环境执行 `ALTER TABLE chunks ADD COLUMN IF NOT EXISTS bbox_mode TEXT CHECK (bbox_mode IN ('precise','block'));` 后列已存在。
- **复测（2026-11-12）**：对 paperId=53 提问返回 `code=0`，`citations[].bboxX0~Y1` 有 0–1 归一化数值，ai-service 日志无 `UndefinedColumn`；`bboxMode` 为 null（该论文解析于补列前，属预期，需重新解析后才能验证 mode）。

---

---

### BUG-020 · papers 列表与详情返回字段与契约不一致（S2 · P4 · 待修复）

- **发现**：2026-11-18 · P1 契约逐字段对账（#54）
- **现象**：
  - `GET /api/papers` 列表项实测只有 `id/title/filename/pageCount/parseStatus/source/createdAt`，**缺契约声明的 `doi` / `arxivId` / `externalUrl`**；同时**多返回 `parseStatus`**（契约的 `Paper` 未定义该字段）
  - `GET /api/papers/{id}` 详情**多返回 `fileSize` / `parseError`**，契约的 `PaperDetail` 未定义
- **影响**：前端只能靠"猜"字段；契约与实现对不上，交接和后续改字段都会踩坑（Alpha 的 BUG-003 同类问题）
- **修法**：二选一，别两头改
  1. 契约 1.3.1 补 `parseStatus`（列表项）、`fileSize`、`parseError`，同时明确 `doi/arxivId/externalUrl` 列表项不返回
  2. 或让实现补齐三个来源字段
- **建议**：走第 1 条（列表页确实不需要 doi/arxivId，契约应当描述现实）

---

### BUG-021 · 检索超时 10 秒与实际链路冲突，导致检索必然降级（S1 · P4 · 已修代码，契约待升）

- **发现**：2026-11-18 · 用户反馈"只有缓存过的关键词有结果"
- **现象**：`curl` 实测直连 arXiv 一次 **9.19 秒**；后端 `app.search.timeout-seconds=10` 且拆成 **两次各 5 秒**，两次都超时 → 全部返回 `degraded=true` + 空列表；只有命中 Redis 缓存的关键词才出结果（如 attention）
- **根因**：超时预算按"境外接口 <5 秒"估的，与校园网实际链路不符
- **修法**：`docker-compose.yml` 增 `APP_SEARCH_TIMEOUT_SECONDS: 30`（每次尝试 15 秒），实测 science 3.4s / agriculture 0.6s / remote sensing 1.1s 恢复
- **待办**：契约 1.3.1 补「检索外部源超时 30 秒、单次尝试 15 秒」，并写明依据
- **修复**：`c7c95af`（11-18）

---

### BUG-022 · citations 缺 readingOrder，契约 1.3.0 新增字段未实现（S2 · P5 · 待修复）

- **发现**：2026-11-18 · P1 契约逐字段对账（#54）
- **现象**：实测 `citations[]` 只有 8 个字段：`page/snippet/chunkId/bboxX0~Y1/bboxMode`，**没有 `readingOrder`**
- **根因**：契约 1.3.0 已冻结该字段（`#52`），但实现侧在 `#86`（引用片段与 reading_order 落库）尚未开工，属排期未到
- **影响**：契约声明了但实现没有 → 若前端此时依赖该字段会拿到 undefined
- **修法**：随 `#86` 落地；在此之前前端**不得**依赖 `readingOrder`（契约已写明可空）
- **状态更新（2026-11-23）**：`#81`（`afdcba6`）已把 `RAG._build_citations` 的 `readingOrder` 补上，**代码侧已修**；但 `chunks.reading_order` 这一列全仓没人建（见 **BUG-027**），所以实际取值恒为 `null`。等 BUG-027 补列并重解析后，本单才真正关闭

---

### BUG-023 · `bboxMode` 按版面类型定值，与 B03 验收互斥（S2 · P1（契约） · 已修复）

- **发现**：2026-11-20 · P1 林子航 · 需求卡交叉复核（B01 vs B03）
- **现象**：同一套文档里两条互斥的验收：
  - 契约 1.3.0 的 `bboxMode` 描述 + B01 验收第 4 条：**双栏页一律 `block`，不得冒充 `precise`**
  - B03 验收第 1 条：**双栏论文 10 题 `bboxMode=precise` 命中 ≥7**
  - 按 1.3.0 口径实现，B03 命中率**恒为 0**——这条验收不可达
- **根因**：`bboxMode` 一开始按**版面类型**（单栏/双栏）定值，而 B03 要的是**框精度**（是否框住那一段、是否跨栏）。维度选错了，不是实现出错
- **影响**：若不改，P2 做 B03 时要么违反契约，要么交不出验收；Review 时两边都能"有理"
- **修法**：契约升 **1.3.1-frozen**，把 `bboxMode` 定义从版面类型改为精度：`precise` = 框覆盖目标段落且不跨栏；`block` = 多块并集 / 跨栏；`null` = 无坐标。单栏双栏不再直接决定取值
- **连带**：B01 验收第 4 条改为精度口径（重排后给不出栏内段落框就如实标 `block`）；`docs/契约/01-api-contract.yaml`、`契约1.3.0-评审要点.md` 第七节同步；**前端不改**（本来就只按三态切样式）
- **复核结论**：Alpha 的「双栏 65/65 全 `block`」在 1.3.0 口径下**合规**，不算缺陷，不单列 Bug
- **修复**：P1 契约 `1.3.1-frozen`（2026-11-20），例会通报，不等回执

---

### BUG-024 · `/api/explain` 不校验论文归属，跨用户可读到他人标题与正文片段（S1 · P4 · 待修复）

- **发现**：2026-11-23 · P1 林子航 · 拉取 #74/#75 提交后代码审查
- **现象**：`#75`（qa + explain + import 三处过滤）已提交 `098b4fc`，但**实际只做了 qa 与 import**：
  - `ExplainController.java` 全文**没有任何 `JdbcTemplate` / `UserContext` 引用**（逐行核对，零命中）
  - 它把前端传来的 `paperId` **原样转发**给 ai-service
  - `ai-service/app/routers/explain.py:38` → `select title from papers where id = %s`
  - `ai-service/app/routers/explain.py:53` → `select content from chunks where paper_id = %s` —— **两处都无 user 维度**
- **可复现路径**：登录用户 A 在划词浮层里传 B 的 `paperId` → 走 `/api/explain` → ai-service 取 B 的标题与匹配到的 chunk 正文拼成上下文 → 译文/释义里带出 B 的论文内容
- **违约点**：契约 1.3.0 `x-conventions.authz` 把**划词解释**明确列为 6 处之一，要求越权一律 **2001 / HTTP 404**，且「越权响应不得携带他人任何业务字段，连标题都不许回显」。当前实现把标题直接喂进模型，泄露面比回显更大
- **根因**：`#75` 的验收是「三处过滤」，但 explain 这一处在 backend 侧没有库访问，容易被当成"无需过滤"跳过；真正的库访问在 ai-service，跨进程后没人认领
- **修法（二选一，建议第 1 条）**：
  1. `ExplainController` 拿到 `paperId` 后先 `SELECT 1 FROM papers WHERE id = ? AND user_id = ?`，查不到直接抛 `PAPER_NOT_FOUND`（2001），再转发
  2. 或把 `userId` 一并传给 ai-service，由 `_load_context` 带 user 条件查
- **附带**：不传 `paperId` 的划词（纯文本翻译）不受影响，**该路径不要一刀切成 401**
- **关联**：`#75`、BUG-025

---

### BUG-025 · `ai-service:8000` 对外发布且 `/internal/*` 无鉴权，可绕过 backend 全部校验（S1 · P6 · 待修复）

- **发现**：2026-11-23 · P1 林子航 · 审查多用户隔离时顺带核对部署面
- **现象**：`docker-compose.yml` 里 `ai-service` 有 `ports: "8000:8000"`，而 `/internal/*`（parse / qa / explain / papers）**没有任何鉴权**，契约 02 也未约定内部令牌
- **影响**：宿主机（含同网段）直接 `POST http://<host>:8000/internal/explain {"paperId": <别人的>}`，即可绕过 backend 的全部校验（文本长度、mode、越权 2001）读他人标题与 chunk 正文。Beta 加了多用户隔离后，这条从"调试方便"升级成**隔离的旁路**
- **性质**：Alpha 就存在，非本次提交引入，但本次提交让它的后果变严重
- **修法（二选一，建议第 1 条）**：
  1. 去掉 `8000:8000` 发布，只让 compose 网络内可达（backend 走 `http://ai-service:8000` 不受影响）；调试需要时临时 `docker compose port`
  2. 或内部加共享令牌：compose 注入 `INTERNAL_TOKEN`，两边比对，缺失/不符回 3003
- **顺带**：若保留发布，至少在 `docs/部署` 里写明"8000 不得暴露到公网"

---

### BUG-026 · `UserContext` 未设置时静默回退 user 1，登录态切换后会变成越权而非报错（S2 · P4 · 已修复）

- **发现**：2026-11-23 · P1 林子航 · 同上
- **现象**：`UserContext.currentUserId()` 在 ThreadLocal 为空时**返回 `1L`**（`UserContext.java:16`），不抛异常、不打日志
- **当前为何不出事**：`app.auth.enforce=${AUTH_ENFORCE:false}` 默认 false，未登录请求本来就该按用户 1 走，Alpha 存量的 12 篇也都在 user_id=1 名下，行为与改造前一致，**无回归**
- **风险**：一旦把 `AUTH_ENFORCE` 打开（#72 注册登录落地后必然要开），任何漏过 JwtFilter 的请求（白名单 URI 精确匹配、加 context-path、`@Async` 线程、将来新增的路径）都会**静默变成用户 1**——不报错、不拦截，直接把别人的数据当自己的读
- **附带**：`JwtFilter.shouldNotFilter` 用 `request.getRequestURI()` 精确比对 `/api/auth/register`、`/api/auth/login`，末尾带斜杠或前面有 context-path 时白名单失效，会把注册/登录也 401 掉
- **修法**：
  1. 回退值改成"按配置"：`enforce=false` 时回退 1（保持兼容并 WARN 一行）；`enforce=true` 时直接抛 `AUTH_TOKEN_INVALID`（6002）
  2. 白名单改用 `endsWith` 或 `AntPathMatcher`
- **判据**：`AUTH_ENFORCE=true` 后，不带 `Authorization` 头请求 `/api/papers` 必须回 **401 / 6002**，而不是返回用户 1 的列表
- **修复**：`134d0e3`（11-24，P4）两条都照修法做了，逐行核对如下：
  - `UserContext.currentUserId()` 改为 ThreadLocal 为空时**抛 `BizException(AUTH_TOKEN_INVALID)`**，不再静默返回 1
  - `JwtFilter` 在 `enforce=false` 且无令牌时**显式** `UserContext.set(1L)` 并打一条 `WARN`（日志里能看见"按 legacy 用户 1 处理"），把隐式兜底摊到明面上
  - `shouldNotFilter` 改用 `getServletPath()` 并剥掉末尾斜杠，白名单不再被 `/api/auth/login/` 或 context-path 打穿
- **未做的一步（如实记）**：本机 Docker 引擎未启动，**没有实跑**「`AUTH_ENFORCE=true` 后无令牌请求 `/api/papers` 应回 401/6002」这条判据，只做了代码核对。Docker 起来后补一次 curl

---

### BUG-027 · `chunks.reading_order` 全仓没有建列语句，#81 的写入永远落不了库（S1 · P6 · 待修复）

- **发现**：2026-11-23 · P1 林子航 · 查看 `#81`/`#87`/`#88` 提交
- **现象**：`#81`（`afdcba6`）把 `reading_order` 的写法做齐了——`chunker.py` 产出、`chunks.py` 按列存在与否动态拼 INSERT、`RAG.py` 探测列后 `as reading_order` 输出、`_build_citations` 回填 `readingOrder`。**独独缺列**：
  - `docs/契约/03-数据库表结构.sql` 的 `chunks` 建表里**没有** `reading_order`（全仓 grep，只命中代码与 `01-api-contract.yaml:867` 的那句 DDL 注释）
  - `scripts/migrate-users-1.1.0.sql` 只补了 `users` 表与 `papers` 外键，**没补** `chunks.reading_order`
  - 因此 `_has_column(cur, "reading_order")` 恒为 False → 每次解析都走「列不存在，跳过」分支 → 入库恒 NULL → `citations[].readingOrder` 恒为 `null`
- **为什么又踩一次**：与 BUG-019（`bbox_mode` 缺列）**同一型**。这次代码侧学乖了（探测列、没列就跳，不会像 BUG-019 那样整条 SQL 炸），但**列本身仍没人建**，于是从"报错"变成"静默为空"——更难发现
- **影响**：① 契约 1.3.0 声明的 `chunks.reading_order` 与 `citations[].readingOrder` 实际永远拿不到值（BUG-022 从"没实现"变成"实现了但恒 null"）；② **B02 的「当前栏判定」按验收要看阅读顺序里最后可见的块**，没数据就退化成按页判定，等于 B02 白做；③ `#82`（`check_reading_order.py` 基线回归）无从验收
- **修法（两处都要，缺一不可）**：
  1. `docs/契约/03-数据库表结构.sql` 的 `chunks` 建表加 `reading_order INT`（契约 01 的口径：页内从 0 起、可空）
  2. `scripts/migrate-users-1.1.0.sql`（或另起 `migrate-reading-order-1.3.0.sql`）加 `ALTER TABLE chunks ADD COLUMN IF NOT EXISTS reading_order INT;`
- **核对不了的一步（如实记）**：本想连容器 `\d chunks` 实测确认，但本机 **Docker 引擎当时未启动**，只做了静态核对。所以此条记为「静态确证、运行环境未核验」，等 Docker 起来后补一次 `docker compose exec postgres psql -U papermind -d papermind -c "\d chunks"`
- **关联**：`#81` `#87` `#88` `#82`、BUG-019、BUG-022

---

## 编号说明

- BUG-008 / BUG-009 沿用 P1 端到端走查（`docs/验收走查/走查表-2026-11-04.md`）的编号。
- 原 BUG-010（无头浏览器渲染卡住）经真机复核为**误判并撤回**，编号腾出后用于「解析超时」。
- BUG-014（前端把 worker 加载失败显示成「无法连接到服务器」）与 BUG-013 同源，已并入 BUG-013 的影响，不单列，故跳过 014。
- BUG-016 为 API Key 未转发（由 P1 并入本表）。
- BUG-017 为 `/api/search` 降级缺 `degraded` 标记（2026-11-10 发现，`8dd04db` 修复，11-11 复测通过）。
- BUG-018 为检索缓存提示时间用 UTC（2026-11-11 发现，待修复）。
- BUG-019 为 `chunks.bbox_mode` 列未创建导致问答全 3001（2026-11-11 发现，S0，待修复）。
- BUG-020/021/022 为 Beta 首轮（2026-11-18）P1 对账与用户反馈产生：字段与契约不一致、检索超时预算错误、readingOrder 未实现。
- BUG-023 为 Beta 次轮（2026-11-20）P1 复核需求卡时发现：契约 `bboxMode` 语义与 B03 验收互斥，改契约不改代码，已随 1.3.1 关闭。
- BUG-024/025/026 为 Beta 代码审查项（2026-11-23）：拉取 `#74`/`#75` 提交后逐行核对多用户隔离，审出 explain 漏过滤、内部服务无鉴权、登录态静默回退三个漏洞。**均为审查产出，不是跑测产出**。
- BUG-027 为同日查看 `#81`/`#87`/`#88` 时发现：`chunks.reading_order` 全仓无建列语句，代码侧探测列后静默跳过——**BUG-019 的同型复发，只是从"报错"变成"静默为空"**。
