# Alpha Bug List

> P7 李义朋 · [#25](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/25) · v0.7 · 2026-11-06 · 测试版本 `master`（容器化）

| 编号          | 版本        | 现象                                                     | 复现                                                                                           | 影响                          | 级别  | 归属  | 状态  |
| ----------- | --------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------- | --------------------------- | --- | --- | --- |
| **BUG-001** | `8ecb98c` | 上传页选完 PDF 只显示绿字「文件格式正确」，没有上传按钮，也不发请求 | 选 `demo-10p.pdf` → 看页面 + F12 Network | 演示第 2 步走不通；F1-01 界面层无法验证 | S0 | P3 | 已修复 |
| **BUG-002** | `8ecb98c` | 上传响应带出磁盘绝对路径 `data.path` | `curl -X POST /api/papers -F "file=@demo-10p.pdf"` | 泄露目录结构；违反建表 SQL「禁止对外暴露」 | S1 | P4 | 已修复 |
| **BUG-003** | `8ecb98c` | `POST /api/papers` 响应缺 `pageCount`、`createdAt`，多 `size`、`path`（列表接口 `GET /api/papers` 字段正确，仅上传接口不符） | 上传任意 PDF 后看响应体，对照契约 `PaperDetail` | 前端按契约取值会拿到 `undefined` | S1 | P4 | 已修复 |
| **BUG-004** | `8ecb98c`／复现于 `410ed69` | `.pdf` 后缀、内容是 docx 的文件被接受入库：`upload()` 只做后缀校验（142 行），已有的 `isPdf()`（195 行）定义后未被调用 | 上传 `2026数据结构基础实验.pdf`（前 8 字节 `50 4B 03 04` 即 `PK`）→ HTTP 200、入库；`curl -F "file=@fake.pdf"` 同样 200 | 脏数据入库；该文件必然解析失败；F1-04 由通过回退为不通过 | S1 | P4 | 已修复 |
| **BUG-005** | `8ecb98c` | 上传 51MB PDF 返回 `5000 服务器内部错误`，而非契约规定的 `1003 文件超过 50MB` | `curl -i -X POST /api/papers -F "file=@big.pdf"`。对照：同内容的 48MB 文件返回 `code=0`，证明与文件内容无关，只取决于大小 | 无法区分“文件太大”和“服务崩了”，用户不知道该改什么 | S2 | P4 | 已修复 |
| **BUG-006** | `8ecb98c` | 解析完成后 `pageCount` 恒为 15、`chunkCount` 恒为 128，与文件无关 | 上传 10 页的 `demo-10p.pdf`，4 秒后 `GET /api/papers/4`，返回 `pageCount:15`、`chunkCount:128` | 列表页数全部错误；F1「10 页 PDF」验收无法证明；切片数失真 | S1 | P4 | 已修复 |
| **BUG-007** | `8ecb98c` | 无访问日志：发请求后控制台只有启动日志和首次请求的懒加载初始化，没有路径、文件名、状态码 | 启动后上传任意 PDF，翻控制台日志，找不到这次请求的任何记录 | 出问题无法定位是哪个请求、哪个文件、什么错误；#23「运行日志可查」不达标 | S1 | P4 | 已修复 |
| **BUG-008** | `7d39ee8` | 解析失败时 `parseError` 只有 `unknown error`，看不出是连不上 AI 还是超时 | 停掉 AI 服务（8000 无监听）后上传任意 PDF，`GET /api/papers/{id}` → `parseError:"unknown error"` | 用户与测试无法定位故障；`#13` 的失败路径不可观测 | S1 | P4 | 已修复 |
| **BUG-009** | `7d39ee8` | 后缀为 `.docx`、内容却是合法 PDF 的文件被接口接受并入库（HTTP 200，`id=6`） | `curl -F "file=@not-a-pdf.docx" /api/papers` → 200 | 前端按后缀拦、接口按内容放行，两层不一致；与 F1-02 判据「`.docx` 应被拒」冲突，需先定口径 | S2 | P4 + P7 | 已修复 |
| **BUG-010** | `7d39ee8` | 上传后解析必然失败：实测 **65.6 秒**后 `parseStatus=failed`、`parseError=request timed out`、`chunkCount=0`，文献不可提问 | 上传 20 页中文论文（1.88 MB），轮询 `GET /api/papers/{id}` 直至 `failed` | 同一文件 AI 直连解析需 **60 秒以上**（65 片），后端上限 **25 秒**（`ParseService.java:64`）→ 必然超时；F1-10 与 F3 正例全部不可测 | S0 | P4 | 已修复 |
| **BUG-011** | `master`（容器化） | 上传时间比本地早 8 小时：`createdAt` 返回 UTC，前端原样显示 | 容器化启动后上传任意 PDF，对比列表时间与实际时间。DB `created_at` 为 `2026-11-06 18:52+08`，接口返回 `2026-11-06T10:52` | 列表时间全部偏差 8 小时；跨时区部署更混乱 | S2 | P4 / P6 | 待修复 |
| **BUG-012** | `master`（容器化） | 一条命令起全栈后上传必然解析失败：`EMBEDDING_FAILED — couldn't connect to hf-mirror.com ... not in cached files` | `docker compose up -d` 后上传 PDF，`GET /api/papers/{id}` → `failed`；`docker compose exec ai-service ls /root/.cache/huggingface` 为空 | 主链断在解析，演示第 3 步之后不可用 | S1 | P6 / P5 | 待修复 |
| **BUG-013** | `master`（容器化） | 阅读页无法加载 PDF：`pdf_worker_min-*.mjs` 被 nginx 以 `application/octet-stream` 返回，浏览器按 ES 模块规范拒绝执行，pdf.js 降级 fake worker 后渲染失败 | 容器起全栈后打开任意论文阅读页；F12 Console 报 `Failed to load module script: ... non-JavaScript MIME type of "application/octet-stream"`；同一 id 的 `/file` 接口 curl 返回 200 / `application/pdf` | 容器环境阅读链路整体不可用（F2 组、E2E-3/5 不可演示）；前端提示误报为「无法连接到服务器」（该文案问题已并入本条影响，不单列） | S1 | P3 / P6 | 待修复 |
| **BUG-015** | `master`（容器化） | `papers.file_path` 存绝对路径，切换运行方式后旧记录文件不可读：宿主机为 `C:\...\backend\uploads\...`，容器内该路径不存在 | 手工运行后端时上传若干论文 → 切到容器运行 → 点开这些论文报「打不开这份文献」 | 同一数据库切换运行环境后旧数据不可用（测试/演示易踩，真实用户少见） | S2 | P4 | 待确定 |
| **BUG-016** | `master`（本地 + 容器） | API Key 设置页填了不生效：`QaController.java:79-82` 组装转发请求时只带 `paperId/question/topK/maxCitations`，把 `apiKey` / `baseUrl` / `model` 丢了，实际用的是服务端 `.env` | 传假 Key 仍正常作答：`curl -X POST /api/qa/ask -H "Content-Type: application/json" -d "{""paperId"":13,""question"":""10-30 那天站会剩余 Issue 是多少？"",""apiKey"":""sk-fake""}"` → HTTP 200（应当认证失败） | 用户自己填的 Key 永远不生效，会认为这个功能是假的；契约 1.0.2 已定义该字段 | S1 | P4 | 待修复 |

级别：**S0** 主链断（演示走不通）· **S1** 验收不达标 · **S2** 体验或契约一致性
（S = Severity 严重程度，与分工编号 P1–P7 区分；归属列的 P3/P4 才是人）

状态：待修复 / 已修复 / **待确定**（待确定 = 是否计为缺陷需例会上共同裁定，暂不入「待修复」）

编号说明：BUG-008 / BUG-009 沿用 P1 端到端走查（`docs/验收走查/走查表-2026-11-04.md`）的编号；原来的 BUG-010（无头浏览器渲染卡住）经真机复核**已撤回**，编号腾出，本条解析超时改用 **BUG-010**。

编号说明补充：BUG-014（前端把 worker 加载失败显示成「无法连接到服务器」）与 BUG-013 同源，已并入 BUG-013 的影响栏，不单独编号；BUG-015 为跳号保留位。
