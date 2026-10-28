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

## 本地开发环境

- JDK 25（编译目标 17）+ Spring Boot 3.5.6
- 依赖：`docker compose up -d` 起 postgres + redis
- 2026-10-28 本地验证：`GET /api/papers` 返回 200 / `code:0`，`?page=0` 返回 400 / `code:1001`
