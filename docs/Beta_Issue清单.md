# Beta 迭代 Issue 清单 · **按人排 · 均衡版**（✅ 已建到 GitHub）

> 团队：七仙过海 · 周期：**D21–D44（2026-11-18 周三 → 2026-12-11 周五，共 24 天）**
> **Day 口径：D21 = 11-18（明天），D44 = 12-11（下下下周周五）**
> **本文档编号 = GitHub issue 号（#51–#101）**，链接：`https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/<号>`
> 状态：**51 条已全部创建**（按人 8/6/6/8/8/8/7），已挂负责人与 `Beta-W1`～`Beta-W4` 里程碑
> 父卡（B01–B20）以 `epic:Bxx` 标签挂在各条 issue 上，不另建 Epic issue
> **日期仅供参考**——认领时可按本人节奏前后挪，但三个硬卡点不能挪

---

## 〇、日历口径

| 周 | 日期 | 天数 | Day 编号 | 里程碑 |
|---|---|---|---|---|
| **W1** | 11-18（三）→ 11-22（日） | **5 天** | D21–D25 | `Beta-W1`（14 条） |
| **W2** | 11-23（一）→ 11-29（日） | 7 天 | D26–D32 | `Beta-W2`（16 条） |
| **W3** | 11-30（一）→ 12-06（日） | 7 天 | D33–D39 | `Beta-W3`（17 条） |
| **W4** | 12-07（一）→ 12-11（五） | **5 天** | D40–D44 | `Beta-W4`（4 条） |

W1 与 W4 各只有 5 天，所以**契约必须早冻、报告不能压到最后两天**。

---

## 一、均衡性自查

| 成员 | 条数 | 变化 |
|---|---|---|
| P1 林子航 | **8** | 契约拆分 + 集成走查 + 文档；**全部不写代码** |
| P2 杨靖 | **6** | 走查转 P1，补样式与首屏 |
| P3 杨绎平 | **6** | 补扫描件提示 |
| P4 刘万礼 | **8** | 合并 3 组 + 检索历史延 RC（原 12 条） |
| P5 吴啸天 | **8** | 合并 2 组（原 10 条） |
| P6 刘征 | **8** | 不变 |
| P7 李义朋 | **7** | 不变 |

**极差 6–8。**

---

## 二、每人明细

### P1 林子航 · **8 条**（全部不写代码）

| Issue | 标题 | 参考日期 |
|---|---|---|
| [#51](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/51) | [契约] auth 四接口 + 错误码 4001/4002 | 11-18 → 11-19 |
| [#52](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/52) | [契约] `chunks.reading_order` + `citations` 字段 | 11-19 |
| [#53](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/53) | [契约] 划词拦截规则 + 越权口径 + 冻结 1.3.0 | 11-19 |
| [#54](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/54) | [契约] 实现与契约逐字段对账 | 11-20 → 11-21 |
| [#55](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/55) | [集成] 双栏端到端走查 | 12-03 |
| [#56](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/56) | [集成] 单栏回归走查 + 与 Alpha 行为对比 | 12-04 |
| [#57](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/57) | [文档] Beta 出口条件定稿 | 12-10 → 12-11 |
| [#58](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/58) | [文档] Beta 演示脚本 + 一次彩排 | 12-09 → 12-10 |

> 「不写代码」的边界：#55 #56 是**跑一遍看结果、写结论**，不改任何源文件。
> **契约冻结 11-19**（#51 #52 #53 三条关单），全组等这一天。

---

### P2 杨靖 · **6 条**

| Issue | 标题 | 参考日期 | 依赖 |
|---|---|---|---|
| [#59](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/59) | [前端] 引用框三态样式统一 + 双栏虚线框图例 | **11-18 → 11-20** | 无 |
| [#60](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/60) | [前端] 长论文首屏渲染优化（>50 页 ≤3 秒） | **11-21 → 11-22** | 无 |
| [#61](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/61) | [前端] 双栏页「当前栏」判定 | 11-25 → 11-26 | #81 |
| [#62](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/62) | [前端] 引用块级跳转 | 11-26 → 11-27 | #81 |
| [#63](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/63) | [前端] 缩放 50%/200% 定位重算 | 11-28 → 11-29 | #62 |
| [#64](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/64) | [前端] 双栏 10 题框套准 + 旋转页对齐 | 12-01 → 12-02 | #83 |

**无依赖的两条（#59 #60）提到 W1**，不干等 #81。
**红线**：不碰 `backend/`、不改契约、不碰 `chunker.py`。

---

### P3 杨绎平 · **6 条**

| Issue | 标题 | 参考日期 | 依赖 |
|---|---|---|---|
| [#65](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/65) | [前端] 扫描件提示（无文字层明确提示需 OCR） | **11-18 → 11-19** | 无 |
| [#66](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/66) | [前端] 登录/注册页静态稿 + 表单校验 | **11-20 → 11-22** | 无 |
| [#67](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/67) | [前端] 划词低质输入拦截 | 11-23 | #53 |
| [#68](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/68) | [前端] 路由守卫 + 登录后回原页 | 11-28 → 11-29 | #72 |
| [#69](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/69) | [前端] token 持久化（刷新不掉线） | 12-01 → 12-02 | #68 |
| [#70](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/70) | [前端] 401 自动登出 + 统一错误提示 | 12-03 → 12-04 | #69 |

**前三条无依赖或依赖已满足，全部提前**；#66 静态稿不等接口。
**红线**：不碰 PDF 渲染核心（P2 地盘）。

---

### P4 刘万礼 · **8 条**（合并后）

| Issue | 标题 | 参考日期 | 依赖 |
|---|---|---|---|
| [#71](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/71) | [后端] JwtFilter + 401 拦截 + 错误码落位 | 11-23 | #87 |
| [#72](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/72) | [后端] 注册 + 登录 + bcrypt + 签发（原两条合并） | 11-24 → 11-26 | #71 |
| [#73](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/73) | [后端] 登录安全自查 | 11-27 → 11-28 | #72 |
| [#74](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/74) | [后端] papers 四处过滤（列表/详情/删除/取文件） | 12-01 → 12-02 | #72 |
| [#75](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/75) | [后端] qa + explain + import 三处过滤 + 越权口径统一（原两条合并） | 12-03 | #74 |
| [#76](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/76) | [后端] 检索双源并发调用 + 结果合并 | 12-01 | #53 |
| [#77](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/77) | [后端] 三级去重 + 稳定排序（原两条合并） | 12-02 → 12-03 | #76 |
| [#78](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/78) | [后端] 非 arXiv 来源导入打通（含 `source` 枚举冲突修复） | 12-04 → 12-05 | #77 |

**削峰顺序**（真做不完时）：先砍 #78 → 再砍 #77 的稳定排序 → **#71–#75 登录安全一条不许砍**。
W1（11-18→11-22）你空着（等 #87），建议先把 JWT 方案与错误码口径跟 P1 敲定，代码等表落地。

---

### P5 吴啸天 · **8 条**（合并后，已表态继续原模块）

| Issue | 标题 | 参考日期 | 依赖 |
|---|---|---|---|
| [#79](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/79) | [AI] 通栏块识别 + 切带（`_split_bands`） | 11-20 → 11-21 | #52 |
| [#80](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/80) | [AI] 栏间空白检测（0.35–0.65 投影法） | 11-21 → 11-22 | #79 |
| [#81](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/81) | [AI] `(band, column, y, x)` 排序 + 写 `reading_order` | 11-23 | #80 |
| [#82](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/82) | [AI] 基线回归 + 3 篇双栏验证 + `check_reading_order.py` | 11-24 | #81 |
| [#83](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/83) | [AI] 按 column 取主栏 bbox，标 `precise`/`block` | 11-30 → 12-01 | #81 |
| [#84](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/84) | [AI] 概览类识别 + 放宽检索路径（原两条合并） | 11-26 → 11-27 | — |
| [#85](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/85) | [AI] 召回回归三组 | 11-28 | #84 |
| [#86](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/86) | [AI] 引用片段截断与碎片过滤（原两条合并） | 12-02 → 12-04 | #81 |

**⛔ 11-24 是硬卡点**：#82 交不出来，P2 的三条与 #86 全断。
**红线**：不改业务接口签名、不碰前端。

---

### P6 刘征 · **8 条**

| Issue | 标题 | 参考日期 | 依赖 |
|---|---|---|---|
| [#87](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/87) | [数据] 建 `users` 表 + 外键 + 建表语句升 1.1.0 | **11-18 → 11-19** | #51 |
| [#88](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/88) | [数据] 迁移脚本（存量归 user_id=1，幂等）+ 存量库实测 | 11-19 → 11-20 | #87 |
| [#89](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/89) | [数据] 旧论文回归（打开 + 提问 + 删除） | **11-21** | #88 |
| [#90](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/90) | [部署] 三端构建 workflow | 11-25 → 11-26 | #53 |
| [#91](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/91) | [部署] 单测 + ai-service 脚本自检 job | 11-27 → 11-28 | #90 |
| [#92](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/92) | [部署] PR 模板 + 故意提坏 PR 验证真被拦住 | 11-30 → 12-01 | #91 |
| [#93](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/93) | [部署] `backup.ps1`（**不备 hf-cache**） | 12-03 | — |
| [#94](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/94) | [部署] `restore.ps1` + 实测还原一次 | 12-04 | #93 |

**⛔ 11-21 迁移必须完成（#87 #88 #89），无降级预案**。**⛔ 不许 `docker compose down -v`**。

---

### P7 李义朋 · **7 条**（已表态继续原模块）

| Issue | 标题 | 参考日期 | 依赖 |
|---|---|---|---|
| [#95](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/95) | [测试] Beta 用例表 v1.0 起草 | **11-18 → 11-22** | — |
| [#96](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/96) | [测试] 检索降级用例：超时 / 断网 | **11-25 → 11-26** | 现有接口即可测 |
| [#97](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/97) | [测试] 检索降级用例：缓存过期 / 429 | 11-27 → 11-28 | #96 |
| [#98](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/98) | [测试] 多用户隔离 9 条交叉用例 | 12-05 → 12-06 | #75 #70 |
| [#99](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/99) | [测试] 隔离结果入用例表 + 异常挂 BugList | 12-06 | #98 |
| [#100](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/100) | [测试] Beta 测试报告（每条带证据来源） | 12-08 → 12-10 | 全部 |
| [#101](https://github.com/lin612320/TeamProject-PaperReadingHelper/issues/101) | [文档] Scrum 博客 + BugList 升版 + 用例表定稿 | 12-10 → 12-11 | #100 |

**#96 #97 提前到 W2**：降级用例用现有单源接口就能测（断网、超时、缓存），不必等去重上线。

---

## 三、周节奏与硬卡点

| 周 | 日期 | 谁在干什么 | 硬卡点 |
|---|---|---|---|
| **W1**（5 天） | 11-18 → 11-22 | P1 契约四条 · P6 建表迁移 · P5 双栏算法 · P2 样式+首屏 · P3 扫描件提示+登录页静态稿 · P7 用例表（**6 人在跑**） | **11-19 契约冻结**（#51 #52 #53） · **11-21 迁移完成**（#87 #88 #89） |
| **W2**（7 天） | 11-23 → 11-29 | P5 双栏数据收官 · P4 登录安全 · P2 定位两条 · P3 守卫 · P6 CI · P7 降级用例 | **11-24 双栏数据 ready**（#82） · 11-26 登录主链通（#72） |
| **W3**（7 天） | 11-30 → 12-06 | P4 过滤+去重 · P2 引用框 · P5 引用质量 · P3 token/401 · P6 备份 · P7 隔离验收 | **12-06 功能冻结** |
| **W4**（5 天） | 12-07 → 12-11 | 全员回归 · P7 报告 · P1 出口条件 + 演示彩排 | **12-11 无 P0，收工** |

---

## 四、跨人依赖（写死）

| 等待方 | 等谁 | 必须哪天 |
|---|---|---|
| #87 | P1 **#51** | **11-19** |
| #79 | P1 **#52** | **11-19** |
| #67 #76 #90 | P1 **#53** | **11-19** |
| #71 | P6 **#87** | **11-20** |
| #61 #62 #83 #86 | P5 **#81** | **11-23** |
| #68 #69 | P4 **#72** | **11-26** |
| #96 | 现有单源接口 | 无需等 |
| #98 | P4 **#75** + P3 **#70** | **12-04** |

---

## 五、并发错峰（同文件不许两人同时动）

| 文件 | 独占人 |
|---|---|
| `frontend/src/views/ReaderView.vue` | **P2** |
| `ai-service/app/services/chunker.py` | **P5** |
| `docs/03-数据库表结构.sql` | **P6** |
| `docs/01-api-contract.yaml` | **P1** |
| `docker-compose.yml` / `.github/` | **P6** |

> P1 的 #55 #56 只读不改文件，不占用独占权。

---

## 六、延 RC（本版削出，**未建 issue**）

| 内容 | 原因 |
|---|---|
| 检索历史：Redis 存/取/清（后端） | P4 已 14 天连轴，削掉低价值项 |
| 检索历史：下拉 + 回填（前端） | 依赖上一条，一并延 |

## 七、仅剩一条可选补充项

| 候选 | 内容 | 建议归谁 |
|---|---|---|
| C1 | 单篇「重新解析」入口（补救卡在 parsing 的论文） | P4（若撑不住，延 RC） |

> 原 C2 扫描件提示 → 已建 **#65**；C3 引用框样式 → **#59**；C4 首屏优化 → **#60**；C5 演示彩排 → **#58**。

---

## 八、已建情况与后续维护

| 项 | 状态 |
|---|---|
| Issue | **51 条，#51–#101**，全部已指派负责人 |
| 里程碑 | `Beta-W1` 14 / `Beta-W2` 16 / `Beta-W3` 17 / `Beta-W4` 4 |
| 标签 | `beta` + 模块（frontend/backend/ai/data/deploy/test/docs）+ 优先级（p1/p2）+ `epic:Bxx` |
| 父卡 | 以 `epic:Bxx` 标签表达，未单建 Epic issue |

**后续维护约定**

- 关单前必须确认提交真的在仓库（P5 提过：不能只看 GitHub 状态）
- 燃尽图只数 issue：51 条 → 每日剩余数
- 新增需求进 Backlog，不插进本轮

## 九、提交纪律（沿用 Alpha）

- commit：`feat|fix|docs|test|chore: 简述 (#IssueID)`
- 每日例会前必须 push
- 签入记录与 Issue 对不上不计工作量

---

*2026-11-17 P1 整理 · 均衡版第 5 稿（编号已换成 GitHub 真实 issue 号）*
