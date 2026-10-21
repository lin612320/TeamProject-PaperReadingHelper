# ai-service · AI / PDF 服务

FastAPI · PyMuPDF · pgvector · DeepSeek / Qwen 兼容接口

## Alpha 范围（只做这些）

| 能力 | Issue | 验收 |
|---|---|---|
| PyMuPDF 文本抽取（blocks 顺序，双栏**先凑合**） | #17 | 段落完整、带页码 |
| 切片 + Embedding 入库 | #18 | 单篇论文可写入 `chunks` 表 |
| 检索 + Prompt + 返回答案与页码 | #19 | 返回答案 + 引用片段 + 页码 |
| 答案质量抽样（10 题） | #20 | 引用页码准确率 ≥ 70% |

## 明确不做（Beta / RC）

双栏阅读流排序算法、bbox 精确定位（Beta 主菜）、跨文献对比 Prompt、重排与成本优化。

## 约定

- 输入输出严格按 `docs/01-api-contract.yaml`，`bbox*` 字段 Alpha 一律返回 `null`
- 切片建议 500–800 字、重叠 100 字，chunk 必须带 `page`（1 起）
- 答案必须基于检索到的段落，无依据时明确说「本文未涉及」，**不许编造**
- token 用量与费用按 `(prompt_tokens*0.001 + completion_tokens*0.002)/1000` 记录，写日志
- 单次问答服务端耗时目标 < 20s，超时返回结构化错误而非挂死

## 目录约定（待 P5 建立）

```
app/
├─ main.py          FastAPI 入口
├─ routers/         路由
├─ services/        pdf_parser.py / chunker.py / embedder.py / rag.py / llm_client.py
└─ db/              连接与模型
```
