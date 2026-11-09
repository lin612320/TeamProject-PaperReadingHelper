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
├─ docker-compose.yml    一键起全栈（postgres + redis + backend + ai-service + frontend）
└─ README.md
```

## 本地启动

```bash
# 1. 一条命令起全栈
docker compose up -d

# 2. 校验
docker compose ps
docker compose logs -f backend
```

> 一条 `docker compose up -d` 起全栈（postgres + redis + backend + ai-service + frontend）。首次会拉取/构建镜像（ai-service 的 torch 镜像约 2GB），耐心等待。
>
> 问答需要 DeepSeek Key：在仓库根目录执行 `cp ai-service/.env.example .env`，填好 `DEEPSEEK_API_KEY`，再 `docker compose up -d`（compose 会自动读取根目录 `.env`）。不填也能起，但提问会报「未配置 DEEPSEEK_API_KEY」。
>
> 改过 `docs/03-数据库表结构.sql` 后，**不要用 `docker compose down -v` 让它生效** —— `-v` 会连 `hf-cache`（2.2GB 向量模型）和 `uploads`（已上传的 PDF）一起删掉，模型没了就要重新联网下载，演示环境直接废掉。
>
> 正确做法二选一：
>
> - **给已有库补列**（推荐，幂等）：把 DDL 里新增的那条 `ALTER TABLE ...` 直接在库里执行一次，例如
>   `docker compose exec -T postgres psql -U papermind -d papermind -c "ALTER TABLE chunks ADD COLUMN IF NOT EXISTS bbox_mode TEXT;"`
> - **确实要重建库**：只删数据卷，别动其它卷 ——
>   `docker compose stop postgres && docker volume rm papermind_pgdata && docker compose up -d postgres`
>   （库里的论文记录会清空，需要重新上传）

## 常见问题

**1. 断网 / 镜像拉取失败**

首次启动需要从 Docker Hub 拉取基础镜像（postgres、redis 等）。网络不通时会看到：

```
failed to resolve reference "docker.io/pgvector/pgvector:pg16":
failed to do request: Head "https://registry-1.docker.io/v2/...": EOF
```

处理办法：

- **有网时先预拉**：`docker compose pull`，成功后再 `docker compose up -d`
- **完全离线**：在有网机器上 `docker compose build`，用 `docker save` 导出镜像、`docker load` 导入
- **注意**：镜像已在本地时，断网不影响启动（`docker compose up -d` 仍可起全栈），只有拉取新镜像才会失败

**2. 上传后解析一直失败（EMBEDDING_FAILED）**

容器内没有 embedding 模型时，上传后会提示向量化失败。首次需将宿主机 `~/.cache/huggingface` 下的 `bge-m3` 拷入 `hf-cache` 卷，详见 `docs/测试/BugList.md` 的 BUG-012。

```powershell
docker run --rm `
  -v "$env:USERPROFILE\.cache\huggingface:/host:ro" `
  -v teamproject-paperreadinghelper_hf-cache:/data `
  redis:7-alpine sh -c "cp -a /host/. /data/"
```

## 分支规范（双分支）

| 分支 | 职责 | 谁能动 |
|---|---|---|
| `master` | 日常集成：功能提交、修改、修复全部进这里 | **全体成员**，直接推送或走 feature 分支合入（分支合入由本人自行操作，不需等组长） |
| `release` | 交付/答辩版本：每组评审通过后才升级一次 | **仅组长林子航**，成员禁止推送 |

- **开发方式自由**：可以直接推 `master`，也可以走 `feature/<issue号>-<简述>` 分支（如 `feature/5-pdfjs-render`）——**允许在分支上慢慢开发，不必每天合**
- **合入时机**：本人认为这条 Issue 做完、能演示了，自己把分支合进 `master`，不需要等组长审批
- **交付口径**：`release` 才是交付版本，由组长在验收节点合并；`master` 一直是"能跑的最新集成版"
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
| `docs/01-api-contract.yaml` | **① 对外接口契约**（浏览器 ↔ Spring Boot，6 个接口） |
| `docs/02-内部服务契约.yaml` | **② 内部服务契约**（Spring Boot ↔ FastAPI，4 个接口） |
| `docs/03-数据库表结构.sql` | **③ 数据库表结构契约**（4 张表完整 DDL） |
| docs/bbox坐标约定.md | 引用高亮坐标建系（P2↔P5 对接标准，#7 结论） |
| `docs/契约评审要点.md` | D3 评审会：20 个拍板点 + 三份评审顺序 |
| `docs/Alpha功能清单.md` | Alpha 四个功能与逐条验收标准 |
| `docs/三轮功能路线图.md` | Alpha / Beta / RC 任务池与七人分工 |
| `docs/Alpha_Issue清单.md` | 28 条 Issue，按 D1–D15 排期 |
| `docs/全员必学清单.md` | D1–D3 全员学习清单与验收方式 |

## 团队

分工细则见 [`docs/团队分工明细.md`](docs/团队分工明细.md)：每人任务包、Issue 编号、责任矩阵、越界红线、接口对接人。

| 编号 | 姓名 | GitHub | 角色 | Alpha 主责 |
|---|---|---|---|---|
| P1 | 林子航 | lin612320 | 组长·架构·集成 | 契约、Compose 骨架、评审、端到端走查 |
| P2 | 杨靖 | star675411 | 前端·PDF 核心 | PDF.js 渲染、翻页缩放、页码跳转 |
| P3 | 杨绎平 | hexag0n1 | 前端·页面 | 上传页、文献列表、问答侧栏 |
| P4 | 刘万礼 | Linyuue | 后端·业务 | 上传 / 文献 CRUD / 转发问答 |
| P5 | 吴啸天 | Cheongfan | AI·RAG | 抽取、切片、检索、答案 + 页码 |
| P6 | 刘征 | lzzzzzasd | 数据·部署 | 建表、Redis、一键启动、日志 |
| P7 | 李义朋 | xingniansky | 测试·文档 | 冒烟用例、Bug List、Scrum 博客 |

详细验收标准见 `docs/三轮功能路线图.md`。

## 国内网络提示

若 `git push` 报 `Connection was reset`（直连被重置）或 `schannel: AcquireCredentialsHandle failed`（证书库问题），按顺序试下面两种方案。

**方案 A：HTTPS + 代理 + openssl 后端**

```powershell
git config --local http.proxy http://127.0.0.1:<你的代理端口>   # mihomo / Clash 的混合端口
git config --local http.sslBackend openssl
```

维护者本机实测端口 `10090`（mihomo）。⚠️ 代理客户端一关就立刻推不动。

**方案 B：SSH over 443（推荐，不依赖代理）**

```powershell
# 1. 生成密钥，把公钥加到 GitHub（Settings → SSH and GPG keys）
ssh-keygen -t ed25519 -C "你的GitHub邮箱"

# 2. 改 remote 与 SSH 端口
git remote set-url origin ssh://git@ssh.github.com:443/lin612320/TeamProject-PaperReadingHelper.git
git config core.sshCommand "ssh -p 443 -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=NUL"

# 3. 验证：看到 "Hi 你的用户名!" 即通
ssh -p 443 -T git@ssh.github.com
```

维护者本机已切至此方案（`git@ssh.github.com:443`），代理关掉也能推。

## Alpha 出口条件

> 上传 PDF 后可在浏览器内阅读，并针对该论文提问获得带引用页码的答案，点击页码可跳转对应页；全流程无 P0 崩溃，一键启动可用。
