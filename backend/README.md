# backend · 业务服务

Spring Boot · PostgreSQL(pgvector) · Redis

## Alpha 范围（只做这些）

| 接口 | Issue | 验收 |
|---|---|---|
| `POST /api/papers` 文件上传 + 本地存储 | #13 | 10 页 PDF < 3s |
| `GET/DELETE /api/papers*` 文献 CRUD | #14 | Postman 全绿 |
| `POST /api/qa/ask` 转发到 FastAPI | #15 | 透传成功，超时有提示 |
| `GET /api/papers/{id}/file` PDF 流 | #13 | PDF.js 能取到文件 |

## 明确不做（Beta / RC）

鉴权与多用户、`/api/search` 实现（Alpha 只在契约里占位）、批注接口、对比接口。

## 约定

- 统一响应 `ApiResponse{code, message, data}`，异常由 `@RestControllerAdvice` 兜底，**不裸抛堆栈**
- 数据库连接走环境变量，默认指向 `docker compose` 起的 `postgres:5432/papermind`
- Alpha 单用户：`user_id` 固定为 1，Beta 再接真实用户
- 调用 ai-service 必须设超时（建议 30s）与降级提示

## 建表要点（P6/#21）

- `papers`：含 `source / doi / arxiv_id / external_url`，为 Beta 检索导入预留
- `chunks`：含 `bbox_x0/y0/x1/y1`，**可空**，Beta 填
- `reading_session`、`annotation`：**空表先建**，RC 用


## 实际对外接口（Alpha）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/papers` | 上传 PDF，返回 `PaperDetail`（`parseStatus=pending`） |
| GET | `/api/papers?page=&size=` | 列表，`created_at DESC`，返回 `{total, items}` |
| GET | `/api/papers/{id}` | 详情 |
| DELETE | `/api/papers/{id}` | 删除记录 + 磁盘文件 |
| GET | `/api/papers/{id}/file` | PDF 二进制流 |
| POST | `/api/qa/ask` | 转发到 ai-service，25s 超时 |
| GET | `/api/redis/ping` | 调试接口，契约外，Beta 前移除 |

## 配置项

| 配置 | 环境变量 | 默认值 |
|---|---|---|
| `spring.datasource.url` | `SPRING_DATASOURCE_URL` | `jdbc:postgresql://localhost:5432/papermind` |
| `spring.data.redis.host` | `REDIS_HOST` | `localhost` |
| `app.upload-dir` | — | `uploads` |
| `app.parse.mock` | `APP_PARSE_MOCK` | `false` |
| `app.parse.force` | `APP_PARSE_FORCE` | `false` |
| `app.parse.timeout-seconds` | `APP_PARSE_TIMEOUT` | `180` |
| `app.ai-service.url` | — | `http://localhost:8000` |

## 与 ai-service 对接的注意

1. **必须用 HTTP/1.1**：JDK `HttpClient` 默认尝试 h2c 升级，uvicorn 不支持，请求体会丢失（表现为 422 body 缺失）。解析调用显式 `.version(HTTP_1_1)`。
2. **超时分级**：解析 180s（后台异步），问答 25s（对齐 02 契约；原文「建议 30s」以契约为准）。
3. **错误码翻译**：内部 `{code, message}` → 对外 1001/1002/2001/2002/2003/3001/3002/5000。
4. **解析异步**：上传只做存盘 + 插 `pending`，后台线程调 ai-service，成功置 `ready`，失败置 `failed` 并写 `parse_error`。
