# 引用 bbox 坐标约定（#7 预研结论）

> 来源：P2 杨靖 `#7 引用 bbox 坐标预研`（原 `.doc` 已转为本文件，字段名按冻结契约统一）
> 对接双方：**P2 杨靖（前端画框/跳转）↔ P5 吴啸天（后端产出坐标）**
> 效力：与 `docs/01-api-contract.yaml` 的 `x-conventions.coordinate` 一致，冲突时以契约为准
> 生效阶段：**Beta**（Alpha 阶段四个 bbox 字段一律返回 `null`）

---

## 一、五条结论

1. **归一化坐标，不用绝对像素**：取值 `0 ~ 1`
2. **相对「当页」宽高**：`x ÷ 页宽`、`y ÷ 页高`
3. **原点在左上角**，x 向右、y 向下
4. **页码用物理页码，从 1 开始**：封面、目录也计入页数，不用 PDF 内置的页码标签（label）
5. **旋转页面不改变建系**：原点仍在左上，分母使用**旋转后用户看到的当页宽高**

---

## 二、字段定义

| API 字段 | 数据库列 | 类型 | 含义 |
|---|---|---|---|
| `page` | `chunks.page` | int | 引用所在页（物理页码，1 起） |
| `bboxX0` | `bbox_x0` | double | 框左上角 x |
| `bboxY0` | `bbox_y0` | double | 框左上角 y |
| `bboxX1` | `bbox_x1` | double | 框右下角 x |
| `bboxY1` | `bbox_y1` | double | 框右下角 y |

> ⚠️ **字段名以 `bbox` 开头**。原 `.doc` 里写的 `x0 / y0 / x1 / y1` 是简写，**实际接口字段必须是 `bboxX0` 等**，否则前端取不到值且不报错。

## 三、取值约束

```
0 ≤ bboxX0 < bboxX1 ≤ 1
0 ≤ bboxY0 < bboxY1 ≤ 1
```

- `(bboxX0, bboxY0)` 是**左上角顶点**
- `(bboxX1, bboxY1)` 是**右下角顶点**
- 允许相等？**不允许**，宽高必须为正

数据库侧对应 CHECK 约束（`docs/03-数据库表结构.sql`）：

```sql
bbox_x0 DOUBLE PRECISION CHECK (bbox_x0 BETWEEN 0 AND 1)
-- y0 / x1 / y1 同理
```

---

## 四、前端怎么用（P2）

```js
// 页码：PDF.js 的 pageNumber 是物理页码，从 1 开始，直接用
pdfViewer.scrollPageIntoView({ pageNumber: citation.page })

// 高亮框：拿到当前页尺寸后换算成像素
const vp = page.getViewport({ scale })
const left   = citation.bboxX0 * vp.width
const top    = citation.bboxY0 * vp.height
const width  = (citation.bboxX1 - citation.bboxX0) * vp.width
const height = (citation.bboxY1 - citation.bboxY0) * vp.height
```

**注意**：换算时用的 `vp.width / vp.height` 必须是**渲染缩放后的当页尺寸**，用旋转后的 viewport。

## 五、后端怎么产（P5）

```python
# page 从 1 开始（PyMuPDF 的 pno 从 0 开始，记得 +1）
rect = block_rect                    # PyMuPDF 给的绝对坐标
page_w, page_h = page.rect.width, page.rect.height   # 注意用 page.rect（已含旋转）

bbox_x0 = rect.x0 / page_w
bbox_y0 = rect.y0 / page_h
bbox_x1 = rect.x1 / page_w
bbox_y1 = rect.y1 / page_h
```

**旋转页**：`page.rect` 已经是旋转后的可视尺寸，`page.mediabox` 是未旋转的原始尺寸。**用 `page.rect`**，用错就会出现"框整体转了 90 度"。

---

## 六、四个常见坑

| 坑 | 现象 | 原因 |
|---|---|---|
| 用了 `mediabox` 而不是 `rect` | 旋转页的框整体偏转 | 分母用了未旋转尺寸 |
| 页码用了 PDF label | 跳转到错页（差封面/目录几页） | 物理页码 ≠ 内置 label |
| 字段名写成 `x0` | 前端取不到，框不显示且**不报错** | 契约字段是 `bboxX0` |
| 缩放时用固定 scale 换算 | 放大后框偏移 | 必须用当前 viewport 尺寸 |

---

## 七、验收（Beta 阶段）

| 检查 | 通过标准 |
|---|---|
| 单篇正常论文 | 点击引用跳到正确页，高亮框覆盖引用句 |
| 旋转 90° 的页面 | 框位置正确、不偏转 |
| 缩放 50% / 200% | 框跟随缩放，仍覆盖引用句 |
| 带封面目录的论文 | 用物理页码，跳转不偏移 |

---

## 八、责任与状态

| 项 | 内容 |
|---|---|
| 结论产出 | P2 杨靖（#7，2026-10-28） |
| 后端实现 | P5 吴啸天（Beta 阶段，#19 完成后接 bbox） |
| 前端实现 | P2 杨靖（Beta 阶段） |
| 契约同步 | P1 林子航（已写入 `x-conventions.coordinate`，契约升 1.0.1） |
