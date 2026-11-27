# Bug List（Alpha + Beta）

> P7 李义朋 · [#25](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/25) · **v1.11 · 2026-11-27** · 测试版本 `master`（容器化）
> 版式：概览表（5 列，一屏可读）+ 每条明细分块。
> **状态：30 条 · 已修复 25 · 不修复 1（BUG-012，接受风险）· 待修复 4**（BUG-020 契约待补、BUG-021 契约待升、BUG-025 隔离、BUG-030 检索无兜底）
> 分区：BUG-001～019 为 Alpha 段；**BUG-020～023 为 Beta 段**（2026-11-18 起，来自 P1 契约对账与用户视角自查）；**BUG-024~031 为 Beta 代码审查/实测项**（2026-11-23 起，Docker 起来后逐条实跑复核）

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
| BUG-022 | S2  | P5        | 已修复 | `citations` 缺 `readingOrder`（契约 1.3.0 已冻结） |
| BUG-023 | S2  | P1（契约）  | 已修复 | `bboxMode` 按版面类型定值，与 B03 验收互斥（文档矛盾） |
| BUG-024 | S1  | P4        | 已修复 | `/api/explain` 不校验论文归属，跨用户读到他人标题与正文片段 |
| BUG-025 | S1  | P6        | 待修复 | `ai-service:8000` 对外发布且 `/internal/*` 无鉴权，绕过 backend 校验 |
| BUG-026 | S2  | P4        | 已修复 | `UserContext` 未设置时静默回退 user 1，开 enforce 后变越权 |
| BUG-027 | S1  | P6        | 已修复 | `chunks.reading_order` 无建列语句，#81 写入永不落库 |
| BUG-028 | S0  | P6        | 已修复 | 存量库没跑 1.1.0 迁移，`users` 表不存在，注册/登录全 500 |
| BUG-029 | S2  | P4        | 已修复 | 数据库异常被错报成 4001 `STORAGE_ERROR`（文件存储失败） |
| BUG-030 | S1  | P4        | 待修复（P1 擅自改过，已撤回） | 检索只有 arXiv 一源且无兜底，arXiv 一限流整条检索变空列表 |
| BUG-031 | S2  | P4 / P2   | 已修复 | 超时预算与文案不一致：前端划词 15s<后端25s；3002 文案写>30s 实际25s |

**统计**：30 条 · 已修复 24 · 不修复 1（BUG-012，接受风险）· 待修复 5

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

### BUG-022 · citations 缺 readingOrder，契约 1.3.0 新增字段未实现（S2 · P5 （S2 · P5 · 已修复 · 2026-11-27 回归）

> **回归（2026-11-27）**：`citations[]` 已含 `readingOrder` 字段（paper 70 响应验证，值可为 `null`）；B13-02 ① 通过。

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

### BUG-024 · `/api/explain` 不校验论文归属，跨用户可读到他人标题与正文片段（S1 · P4 （S1 · P4 · 已修复 · 2026-11-27 回归）

> **回归（2026-11-27）**：重建 backend 后，A 用 B 的 `paperId=69` 调 `/api/explain` → **HTTP 404 + 2001**；A 用自己的论文仍 200 正常；I-06 通过。

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
- **实测确证（2026-11-24，容器内跑通）**：起 Docker 后建了一个探针账号 `probe_check_01`（id=2，名下 0 篇文献），拿它的令牌做两个对照：

  | 请求 | 结果 | 是否符合契约 |
  |---|---|---|
  | `GET /api/papers`（用户 2） | `total=0` | ✅ 隔离生效 |
  | `GET /api/papers/50`（用户 2 读用户 1 的论文） | **2001 / HTTP 404** | ✅ 隔离生效 |
  | `POST /api/explain` + `paperId=50`（用户 2） | **code=0 / HTTP 200**，返回的释义里写着「在**本文语境中**，它可能作为融合地理矢量与遥感影像的特征提取或决策模型组件」 | ❌ **越权** |

  第三行是关键：`id=50` 是用户 1 的《开放地理矢量与遥感影像的决策级融合……》，用户 2 名下没有任何文献，却拿到了由**别人的论文标题与正文**推出来的释义。**不是理论风险，是当场复现**。而同一批改造里 `papers` 三处都做对了，唯独 explain 漏掉——说明漏的原因是"忘了"，不是"不会"。
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
- **实测核验（2026-11-24，Docker 起后补做）**：临时注入 `AUTH_ENFORCE=true` 重启 backend，逐条对判据：

  | 请求 | 实测 | 契约要求 | 结论 |
  |---|---|---|---|
  | 无令牌 `GET /api/papers` | **6002 / HTTP 401** | 6002 / 401 | ✅ 通过 |
  | 无令牌 `GET /api/auth/me` | **6002 / HTTP 401** | 6002 / 401 | ✅ 通过 |
  | `POST /api/auth/login`（白名单） | 400（参数问题），**未被 401 挡** | 不应 401 | ✅ 通过 |
  | `POST /api/auth/login/`（带尾斜杠） | 404「接口不存在」，**未被 401 挡** | 不应 401 | ✅ 通过 |

  即：`AUTH_ENFORCE=true` 后，不再有任何请求会静默落到用户 1。**本单实测关闭。**（测完已把 `AUTH_ENFORCE` 恢复默认 false）

---

### BUG-027 · `chunks.reading_order` 全仓没有建列语句，#81 的写入永远落不了库（S1 · P6 （S1 · P6 · 已修复 · 2026-11-27 回归）

> **回归（2026-11-27）**：补齐 `reading_order` 列并重建 ai-service 后，paper 71 的 `reading_order` 有值、0 起、同页单调不减；**B01-03 / B05-01 / B13-02 全部回归通过**。

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
- **实测确证（2026-11-24，容器内 `\d chunks`）**：`chunks` 现有 13 列——`id / paper_id / chunk_index / page / content / char_count / token_count / bbox_x0~y1 / embedding / created_at / bbox_mode`，**确实没有 `reading_order`**。BUG-027 由「静态推断」升级为「运行环境确证」
- **关联**：`#81` `#87` `#88` `#82`、BUG-019、BUG-022

---

### BUG-028 · 存量库从未执行 1.1.0 迁移，`users` 表不存在 → 注册/登录全部 500（S0 · P6 · 已修复）

- **发现**：2026-11-24 · P1 林子航 · 起 Docker 后实测 auth 链路
- **现象**：
  - `docker compose exec postgres psql -c "\d users"` → **`relation "users" does not exist`**
  - `pg_constraint` 里查不到 `fk_papers_user` → 外键也没建
  - `POST /api/auth/register` → **HTTP 500，`{"code":4001,"message":"数据库访问异常"}`**
  - `POST /api/auth/login` → 同样 500 / 4001
- **根因**：`docs/契约/03-数据库表结构.sql` 只挂载为 `docker-entrypoint-initdb.d/01-schema.sql`，**仅在数据目录为空时执行**；存量库（`papermind_pgdata` 卷）永远走不到。P6 另写了 `scripts/migrate-users-1.1.0.sql`，但**这个环境里没人跑过**——`#88`「存量库实测」关单了，实测的显然不是这台开发库
- **影响**：**注册/登录完全不可用**（S0 级：Beta 出口条件「登录多用户」直接卡死）。而且前端 `#70` 路由守卫上线后会一片空白
- **修复（2026-11-24 已执行）**：`Get-Content scripts/migrate-users-1.1.0.sql -Raw | docker compose exec -T postgres psql -U papermind -d papermind`，输出 `CREATE TABLE / INSERT 0 1 / setval 1 / UPDATE 0 / DO`，全部成功。迁移后实测：

  | 步骤 | 结果 |
  |---|---|
  | `users` 表 | ✅ 建成，只有 `id=1 legacy`（`password_hash='!disabled'`，不可登录） |
  | `fk_papers_user` | ✅ 外键存在（`contype=f`） |
  | `POST /api/auth/register` | ✅ code=0，返回 token，`expiresAt=2026-11-25T07:41:35+08:00`，`user.id=2` |
  | `GET /api/auth/me` 带令牌 | ✅ 200，返回 `id=2 / username / createdAt` |
  | 重复注册同名 | ✅ **6003 / HTTP 400** |
  | 正确密码登录 | ✅ 200 + token |
  | 错误密码登录 | ✅ **6001 / HTTP 401** |
  | 不存在用户登录 | ✅ **6001 / HTTP 401**（与密码错同一个码，防探测） |

  `setval` 那步验证到位：legacy 占 id=1，新注册拿到 **id=2**，没有撞号。
- **仍需做的事（流程，不是代码）**：
  1. 把「存量库要单独跑迁移」写进部署手册与出口条件检查单，**新环境起完必须核一次 `\d users`**
  2. 探针账号 `probe_check_01` 已删，`users` 里只剩 `legacy` 一行
  3. 建议在 `StartupChecker` 里加一条：启动时若 `users` 表缺失就 WARN 打印迁移命令（跟 BUG-019 的教训一致——缺列/缺表要能自检出来）

---

### BUG-029 · 数据库异常被错报成 4001 `STORAGE_ERROR`（文件存储失败），文案与码位语义不符（S2 · P4 · 已修复 · 2026-11-27 回归）

> **回归（2026-11-27）**：空库 + 临时后端（`SPRING_DATASOURCE_URL` 指向 `pm_migtest`），`POST /api/auth/register` → `{"code":5001,"message":"服务暂时不可用，请稍后重试"}` + **HTTP 500**；不再返回 4001。

- **发现**：2026-11-24 · P1 林子航 · 上面那条 500 的响应
- **现象**：`GlobalExceptionHandler.handleDb()` 把 `DataAccessException` 统一映射成 `ErrorCode.STORAGE_ERROR`，返回 **4001 /「数据库访问异常」/ HTTP 500**
- **违约点**：契约 1.0.0 里 **4001 = `STORAGE_ERROR` =「文件存储失败」**，是给上传落盘用的。数据库异常复用它，会有两个后果：
  1. **前端按契约做映射时会把"数据库挂了"显示成"文件存储失败"**，用户以为是自己 PDF 的问题，排查方向直接被带偏
  2. 4001 从此一码两义，日志与告警没法区分「磁盘/卷挂了」和「SQL 报错」
- **实测证据**：`POST /api/auth/register` 在 `users` 表缺失时返回 `{"code":4001,"message":"数据库访问异常"}` —— 一个"注册失败"却报"存储错误"
- **修法（建议第 1 条）**：
  1. 契约升版，新增 **`5001 DATABASE_ERROR` / HTTP 500 /「数据库访问异常」**（500 段原本只有 5000 INTERNAL，正是为此留的），实现里 `DataAccessException → 5001`
  2. 退而求其次：复用 `5000 INTERNAL_ERROR`，但把 message 说清是数据库侧；**4001 只留给文件存储**
- **注意**：别把这条和 BUG-020/021 那批「契约落后于实现」混在一起改，它是「实现用错码位」，改契约的同时必须改代码
- **关联**：BUG-028（正是它暴露了这条）

---

### BUG-030 · 检索只有 arXiv 一个源且无兜底：arXiv 一限流，整条检索就废成空列表（S1 · P4 · 待修复）

- **发现**：2026-11-24 · P1 林子航 · 用户反馈「检索功能好像又坏了」
- **现象**：`GET /api/search?keyword=attention` → **27.96 秒**后返回 `{"total":0,"degraded":true,"items":[]}`，提示「外部数据源不可用」。连之前能出缓存的 `attention` 都空了
- **实测定位（容器内逐条打，不是猜的）**：

  | 探测 | 结果 |
  |---|---|
  | `curl http://export.arxiv.org/...` | **301** → 跳 `https://`（0.12s） |
  | `curl https://export.arxiv.org/...` | **429 Too Many Requests**（0.42s）← 出口 IP 被 arXiv 限流 |
  | `curl https://api.openalex.org/works?...` | **200**（1.47s）← 另一个源活得好好的 |
  | `/api/search?keyword=attention&source=openalex` | **200 / 1.66s / 真实结果** |

- **根因（三层，缺一层都不会这么难看）**：
  1. **没有兜底**：`source` 默认 `arxiv`，OpenAlex 只在显式传 `source=openalex` 时才用。arXiv 一挂，接口就只会返空——`#76`（双源并发 + 结果合并）还没做，但连最朴素的"失败就换源"都没有
  2. **429 被当成普通异常**：`fetchOnce` 对非 200 统一抛 `IllegalStateException`，`fetchWithRetry` 只捕 `HttpTimeoutException` / `IOException` → 限流时不重试（这点是对的）但上层也不知道"这是限流"
  3. **预算死等**：`timeoutSeconds=30`，两次各 15 秒 → arXiv 不返回时用户干等半分钟才看到空列表
- **建议修法（给 P4，参考做法，不是已落地的代码）**：
  1. `ArxivClient` 对 429/403 单独抛一个可识别异常，**不进重试**（限流时重试只是把预算耗光）
  2. `fetchWithRetry` 单次上限封顶 **8 秒** → 最坏 16 秒就交给兜底，不再卡 30 秒
  3. `SearchController` 在 arXiv 失败后**回落 OpenAlex**：成功则 `degraded=false` 正常返回（契约字段不变），两源都失败才 `degraded=true`
- **⚠️ 处置记录（2026-11-24，必须留档）**：P1 当时**擅自把上面三条改进了 `ArxivClient.java` 与 `SearchController.java` 并推送了 `5037cc6`**，违反了本项目自己定的规矩——「发现偏差不改代码，只记账（改代码归各模块负责人）」，而这两处是 **P4 的地盘**（`#76` 在他手上）。经用户指出后**已回退**：两个 Java 文件恢复到 `29288a0` 的原样，代码零改动，本条目回到「待修复」。此教训写在这里，不隐藏。
  - 回退后 P1 试跑过的那版实测数据（4.99s 出真实结果）**不能作为验收证据**，因为代码已不在仓库里
- **遗留（交给 `#76` 一起做）**：
  1. 现在是"失败后串行回落"，`#76` 要的是**双源并发 + 结果合并**，届时本兜底可删
  2. arXiv 限流是外部因素，长期要么加 `mailto`/合规 UA，要么接受"以 OpenAlex 为主源"
  3. **顺带发现一处配置名不一致**：`docker-compose.yml` 注入 `APP_SEARCH_TIMEOUT_SECONDS`，而 `application.properties` 写的是 `${APP_SEARCH_TIMEOUT:10}`。现在能生效是靠 Spring 的宽松绑定拿环境变量覆盖了文件里的值，**两个名字并存，改一个不生效会很难查**，建议统一成 `APP_SEARCH_TIMEOUT_SECONDS` 并删掉 `application.properties` 里那句占位符
- **关联**：BUG-021（上一轮超时预算问题）、`#76`

---

### BUG-031 · 超时预算与错误码文案不一致：前端划词 15s < 后端 25s，`3002` 文案写「>30s」但 25s 触发（S2 · P4 / P2 · 已修复 · 契约 1.3.3）

> **修复（2026-11-27，契约 1.3.3）**：`qa_ask_seconds` 30 → **25**（与前端 abort / 后端 / ai-service 一致）；`3002` 文案改「AI 服务超时（>25s）」；新增 `explain_seconds: 15`，明确划词前端 15 秒先撤。代码无需改动，口径已对齐。

- **发现**：2026-11-26 · P7 李义朋 · 超时专项测试（故障注入）
- **现象 1（前端预算偏小）**：`/reader` 划词翻译时，前端 `papers.js` 用 `AbortController` **15 秒**取消；后端 `ExplainController` 上限 **25 秒**。实测页面约 15s 弹「解释服务响应超时（>15s）」，而后端仍在跑，curl 25.04s 才返回 `3002`。
- **现象 2（文案与阈值不符）**：契约错误码表中 `3002` 的 message 为「AI 服务超时（>30s）」，但 `QaController`/`ExplainController` 实际在 **25 秒**抛 `3002`；用户会以为要等 30 秒。
- **根因**：
  1. 前端超时值是各自硬编码（问答 25000ms、划词 15000ms），未与后端预算对齐；
  2. 契约 `3002` 的文案仍按早期 30 秒描述，未随 25 秒上限更新。
- **影响**：
  - 划词场景前端先取消、后端白跑约 10 秒（浪费一次 LLM 调用）；
  - 用户看到的「>15s / >30s」与实际阈值不一致，排错和预期管理受影响；
  - 不涉及数据正确性，属体验与一致性问题。
- **期望**：
  1. 前端超时统一 ≥ 后端 + 缓冲（建议划词 28s、问答 28–30s）；
  2. 契约 `3002` 文案改为「AI 服务超时（>25s）」，或把实现上限调到文案一致（二选一，别两头不一致）。
- **参考**：`frontend/src/api/papers.js`（15000/25000）、`ExplainController`（25s）、`QaController`（25s）、契约 `x-conventions.timeout`（`qa_ask_seconds: 30` / `upstream_ai_seconds: 25`）。
- **证据**：`docs/beta/测试/超时专项测试汇总.md` §三.4 / §三.7、`docs/beta/测试/证据/补充-前端划词15s-2026-11-26.txt`。

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
- BUG-028/029 为 2026-11-24 起 Docker 后实跑 auth 链路暴露：`users` 表根本没建（迁移没在本环境执行过），以及 DB 异常被映射成 4001 文件存储错误。**这两条只有真跑才会露出来，读代码读不出来**。
- BUG-030 为 2026-11-24 用户报「检索又坏了」后定位：arXiv 把本机出口限流成 429，而系统只有一个源、没有兜底。**同一时间 OpenAlex 是好的**——所以问题不在网络，在"只押一个源"这个设计。**P1 曾擅自改代码，已回退，本条仍待 P4 修。**
- BUG-031 为 Beta 执行期发现（2026-11-26）：前端划词 15s < 后端 25s、`3002` 文案 >30s 与实际 25s 不符；属超时一致性问题（S2）。
