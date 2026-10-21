# frontend · 前端

Vue 3 + Element Plus + PDF.js + ECharts

## Alpha 范围（只做这些）

| 功能 | Issue | 验收 |
|---|---|---|
| 上传页（含非 PDF 错误提示） | #9 | 传 `.docx` 出现红字提示 |
| 文献列表页 | #10 | 刷新后列表仍在 |
| 问答侧栏（loading / 错误态） | #11 | 提问中显示 loading，失败可重试 |
| PDF.js 单栏渲染 + 翻页缩放 + 页码跳转 | #5 #6 #8 | 打开即渲染，跳第 3 页准确 |

## 明确不做（Beta / RC）

双栏阅读流、引用 bbox 高亮层、登录态、检索页、批注书签、ECharts 看板。

## 约定

- 接口地址走 `VITE_API_BASE`，默认 `http://localhost:8080`
- 统一响应 `{code, message, data}`，`code !== 0` 一律走统一错误提示
- 后端未就绪时用 mock（Postman Mock / MSW），**不许等接口**
- 路由预留 `/compare`、`/dashboard` 空页（RC 填充）

## 目录约定（待 P3 建立）

```
src/
├─ api/          接口封装（按契约生成或手写）
├─ views/        页面
├─ components/   通用组件
├─ stores/       Pinia
└─ router/
```
