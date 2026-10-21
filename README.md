# PaperMind · 论文阅读助手

> 中国海洋大学 · 软件工程 · 七仙过海团队
> 让科研新手「读得懂、问得清、记得住、看得见成长」的智能论文精读平台

**仓库**：https://github.com/lin612320/TeamProject-PaperReadingHelper （产品名沿用 PaperMind）

## 一句话架构

```
Vue 3 + PDF.js + Element Plus   →   Spring Boot（业务底座）  →   FastAPI（AI/PDF 服务）
                                        ↓                              ↓
                              PostgreSQL + pgvector            本地文件存储
                                        ↓
                                     Redis（缓存）
```

## 目录结构

```
PaperMind/
├─ docs/                 设计与迭代文档（契约、分工、Issue、功能清单）
├─ frontend/             Vue 3 + PDF.js + Element Plus
├─ backend/              Spring Boot 业务服务
├─ ai-service/           FastAPI：PDF 解析 / 切片 / 检索 / 问答
├─ docker-compose.yml    本地依赖编排（pgvector + Redis，应用服务待接入）
└─ README.md
```

## 本地启动

```bash
# 1. 起依赖（当前可用）
docker compose up -d

# 2. 校验
docker compose ps
docker compose logs -f postgres
```

> 应用服务（frontend / backend / ai-service）容器尚未接入，见 `docker-compose.yml` 内 TODO。待各自 Dockerfile 就绪后启用，目标是一条 `docker compose up` 起全栈（Issue #2）。

## 分支规范（双分支）

| 分支 | 职责 | 谁能动 |
|---|---|---|
| `master` | 日常集成：功能提交、修改、修复全部进这里 | **全体成员**，直接推送或走 feature 分支合入 |
| `release` | 交付/答辩版本：每组评审通过后才升级一次 | **仅组长林子航**，成员禁止推送 |

- 成员可选走 `feature/<issue号>-<简述>` 分支（如 `feature/5-pdfjs-render`）再合入 `master`
- `release` 只在 Alpha / Beta / RC 三个验收节点由组长合并，合并后在 commit message 标注版本
- 不设长期 `develop` 分支（7 人 2.5 周，避免分支漂移）

## 提交规范

```
feat|fix|docs|test|chore: 简述 (#IssueID)
```

例：`feat: PDF.js 单栏渲染接入 (#5)`

**commit 必须带 Issue 编号**——Scrum Meeting 的签入记录要与 Issue 一一对应，否则评审不计工作量。

完整推送纪律（分支、时机、四步自检、冲突处理、禁止提交项、后果）见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 文档索引

| 文档 | 内容 |
|---|---|
| `docs/团队分工明细.md` | **七人分工、任务包、责任矩阵、越界红线、接口对接人** |
| `CONTRIBUTING.md` | **贡献规范：分支、提交格式、推送纪律、禁止提交项（新人必读）** |
| `docs/01-api-contract.yaml` | 接口契约（v0.1 草案，D3 冻结） |
| `docs/Alpha功能清单.md` | Alpha 四个功能与逐条验收标准 |
| `docs/三轮功能路线图.md` | Alpha / Beta / RC 任务池与七人分工 |
| `docs/Alpha_Issue清单.md` | 28 条 Issue，按 D1–D15 排期 |
| `docs/全员必学清单.md` | D1–D3 全员学习清单与验收方式 |

## 团队

分工细则见 [`docs/团队分工明细.md`](docs/团队分工明细.md)：每人任务包、Issue 编号、责任矩阵、越界红线、接口对接人。

| 编号 | 角色 | Alpha 主责 |
|---|---|---|
| P1 林子航 | 组长·架构·集成 | 契约、Compose 骨架、评审、端到端走查 |
| P2 | 前端·PDF 核心 | PDF.js 渲染、翻页缩放、页码跳转 |
| P3 | 前端·页面 | 上传页、文献列表、问答侧栏 |
| P4 | 后端·业务 | 上传 / 文献 CRUD / 转发问答 |
| P5 | AI·RAG | 抽取、切片、检索、答案 + 页码 |
| P6 | 数据·部署 | 建表、Redis、一键启动、日志 |
| P7 | 测试·文档 | 冒烟用例、Bug List、Scrum 博客 |

详细验收标准见 `docs/三轮功能路线图.md`。

## 国内网络提示

若 `git push` 报 `Connection was reset`（直连被重置）或 `schannel: AcquireCredentialsHandle failed`（证书库问题），按顺序执行：

```powershell
git config --local http.proxy http://127.0.0.1:<你的代理端口>   # mihomo / Clash 的混合端口
git config --local http.sslBackend openssl
```

当前维护者本机实测可用端口为 `10090`（mihomo）。组员按自己客户端的端口填写。

## Alpha 出口条件

> 上传 PDF 后可在浏览器内阅读，并针对该论文提问获得带引用页码的答案，点击页码可跳转对应页；全流程无 P0 崩溃，一键启动可用。
