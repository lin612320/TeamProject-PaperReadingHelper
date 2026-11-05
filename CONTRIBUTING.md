# 贡献规范（CONTRIBUTING）

> 七仙过海团队 · 论文阅读助手 PaperMind
> **新人第一件事：读完本文件再动代码。** 全部规则以本文为准，聊天记录里的口头约定不算。
> 相关文档：`README.md`（项目总览）· `docs/团队分工明细.md`（谁负责什么）· `docs/Alpha_Issue清单.md`（领任务）

---

## 0. 新手接入（3 分钟）

```powershell
# 1. 克隆
git clone https://github.com/lin612320/TeamProject-PaperReadingHelper.git
cd TeamProject-PaperReadingHelper
git checkout master

# 2. 配置你的提交身份（必须，否则作者是别人）
git config user.name  "你的名字"
git config user.email "你的GitHub邮箱"

# 3. 直连不通时配代理（报 Connection was reset 才需要）
git config --local http.proxy http://127.0.0.1:<你的代理端口>
git config --local http.sslBackend openssl
```

> 中文文件名乱码时执行：`git config --global core.quotepath false`

---

## 1. 分支纪律

| 分支 | 谁能推 | 规则 |
|---|---|---|
| `master`（默认） | **全体成员** | 日常开发全推这里；可直接推，也可走 `feature/` 分支合入 |
| `release` | **仅组长林子航** | 已加保护规则，成员推送会被拒绝；每组验收节点由组长合并一次 |
| `feature/<issue号>-<简述>` | 创建者本人 | 例 `feature/5-pdfjs-render`；合并后删除 |

- ❌ 禁止对 `master` / `release` 执行 `git push -f`
- ✅ 只有自己尚未共享的 `feature` 分支允许 force push
- 不设长期 `develop` 分支（7 人 2.5 周，避免分支漂移）

---

## 2. 提交信息规范

**格式强制**：`类型: 描述 (#Issue编号)`

| 类型 | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | 缺陷修复 |
| `docs` | 文档 |
| `test` | 测试 |
| `chore` | 构建、配置、杂务 |

```text
✅ feat: PDF.js 单栏渲染接入 (#5)
✅ fix: 引用页码跳转偏差 (#19)
✅ docs: 补充分支规范 (#0)

❌ 修改了一下                  （没有类型、没有 Issue 号）
❌ feat: 改了很多东西 (#5)      （一个 commit 干了一堆事）
```

- **一条 commit 只做一件事**：既改前端又改后端的拆成两条
- Issue 编号必须来自 `docs/Alpha_Issue清单.md`；纯文档类可用 `(#0)`

---

## 3. 推送时机

1. **每日例会前必须 `git push`**，推不上去视同当日任务未完成
2. 当天任务当天推，**不许攒三天一次推**（签入记录会露馅）
3. 收工前 5 分钟检查 `git status`，不要把半成品留到第二天

---

## 4. 推送前四步自检

```powershell
git pull --rebase          # 1. 先同步，别制造冲突
git status                 # 2. 看清到底要提交什么
git diff                   # 3. 确认没有调试代码、print、临时文件
git add <具体文件>          # 4. 用文件名，不用 git add .
```

- ❌ **禁用 `git add .` 直接提交**，容易把 `.env`、测试 PDF、日志带上去
- `.gitignore` 已拦 `node_modules/` `target/` `__pycache__/` `.env` `uploads/` `*.db`，但**自己的临时文件要自己看**

### 4.1 构建门禁（11-03 事故后新增，强制）

**「我本地能打开」不算通过，构建通过才算。**

```powershell
cd frontend; npm run build          # Vue 编译 + SFC 语法检查
cd backend;  mvn -q -DskipTests package
```

- 构建报错 → **修完再推**，不许「先推上去让别人发现」
- 为什么不靠肉眼看：`.vue` 文件里 `<script>` 是 JS（`//` 合法），`<style>` 是 **CSS（只认 `/* */`）**。在 `<style>` 里写 `//`，整段样式连同后面的规则一起失效，本地开发服务器可能还开着（没触发重编），但别人拉下来就是**整站白屏**
- 这类错 `npm run build` 一定报，肉眼一定漏

---

## 5. 冲突处理

```powershell
git pull --rebase
# 解冲突 → git add <文件> → git rebase --continue
git push
```

- ❌ 冲突时 `git push -f` 一把梭
- ✅ 解不了立刻喊对应模块的人，对照 `docs/团队分工明细.md` 的「接口对接人」表

---

## 6. 绝对不许进仓库的内容

| 内容 | 原因 |
|---|---|
| `.env`、API Key、数据库密码 | 泄露即事故，公网可查 |
| `node_modules/`、`target/`、`__pycache__/` | 仓库膨胀、clone 变慢 |
| 测试用 PDF、上传的论文原文件 | 版权 + 体积，测试数据放本地 `data/` |
| 单个大于 10MB 的文件 | 图片可以，数据集不行 |
| `.idea/`、`.vscode/`、`*.iml` | 个人 IDE 配置 |

---

## 7. 推不上去先查这两件事

| 报错 | 原因 | 处理 |
|---|---|---|
| `Connection was reset` / `schannel` | 直连被重置 | 按 `README.md`「国内网络提示」配代理 + `openssl` 后端 |
| `403` / `Permission denied` | 还没接受邀请 | 去 GitHub 通知或邮件点 **Accept** |

---

## 8. 后果说明

| 行为 | 后果 |
|---|---|
| commit 不带 Issue 号 | 答辩时签入记录对不上，**该条工作量不计** |
| 例会前没 push | 当日任务按未完成记录进燃尽图 |
| 擅自推 `release` | 被保护规则拒绝，并在例会说明 |
| 把密钥/密码推上去 | 立即 `git rm --cached` 删除并**轮换密钥**，不要只删文件 |
| 不按 Issue 开发（自行加功能） | 视为违反「新需求进 Backlog」禁令，改动被打回 |

---

## 9. 提交前自查清单（复制到 PR 或例会发言）

```text
[ ] 已 pull --rebase，本地无冲突
[ ] commit 格式为 类型: 描述 (#Issue)
[ ] 未提交 .env / 密码 / 测试 PDF / 依赖目录
[ ] **构建通过**（cd frontend && npm run build），不只是「本地能打开」
[ ] 改过校验/删除过代码？已 `git blame` 确认这段为什么存在（见 §10.1）
[ ] 改过校验？相邻用例一起复测了（如改 F1-02 必跑 F1-04）
[ ] 已更新对应 Issue 状态
[ ] 改动范围在自己模块内（见 docs/团队分工明细.md 越界红线）
```

---

## 10. 已踩过的坑（写下来避免重犯）

| 日期 | 现象 | 根因 | 已落地的规矩 |
|---|---|---|---|
| 11-03 | 中午还能打开的页面，下午**整站白屏**，三个人先后怀疑是合并冲突、是别人改的文件 | `ReaderView.vue` 的 `<style>` 块里写了 `//` 注释。`.vue` 里 `<script>` 是 JS（`//` 合法）、`<style>` 是 CSS（只认 `/* */`），写法混用导致整个样式块失效 | 见 4.1 构建门禁；已在 `39e56a8` 修复 |
| 11-03 | 有人说「不如直接 force push 一下」 | 想省事跳过冲突处理 | §5 + §8：**任何人不得 force push 到 master**；`release` 只由组长在合并节点推送 |
| 11-02 | 博客附件发给助教，图片全是空白 | `.md` 里写的是相对路径 `images/xxx.png`，别人电脑上没有这个目录 | 对外交付一律出 **PDF（图片内嵌）**，别直接发 `.md` |
| 11-05 | 伪装 PDF 又能上传了：1.9KB 纯文本改名 `.pdf` → **HTTP 200，脏文件入库** | 在 `upload()` 里加后缀校验时，**把 `isPdf()` 的调用删掉了**。方法还在 `PaperController.java:195`，但全后端零调用，成了死代码 —— 上一个 bug（BUG-004）的修复被顺手清掉了 | 见下方 §10.1「改校验先看清它为什么存在」；`410ed69` 引入，待修复 |

**共同点**：这四条都不是「不会写代码」，而是**没有在动手/推送前跑一次能发现问题的那条命令**。

### 10.1 改校验、删代码之前，先看清它为什么存在（11-05 新增，强制）

**现象**：为了修「后缀是 `.docx`、内容是 PDF 被拒」这个问题，加了后缀校验，结果把「内容不是 PDF 却按 PDF 收」的防线一起拆了 —— 一个 bug 修好，另一个 bug 回来了。

**规矩**：

1. **动校验逻辑前，先 `git blame` / `git log -S` 看这行是谁为什么加的**。一行 `if (!isPdf(file))` 背后通常写着某个 Issue 编号，那不是冗余代码，是别人的防线。
2. **加校验不要替换校验，要叠加**。本项目的上传校验必须两段都在：
   - 先查后缀（快速拒绝，挡住 `.docx`）
   - 再查文件头（`%PDF`，挡住伪装）
   - 少一段就漏一类，两类文件各不相同
3. **改完把相邻用例一起跑**：改了 `F1-02` 相关逻辑，就把 `F1-04`（伪装 PDF）一起复测；只跑自己那一条，回归永远发现不了。
4. **删掉的代码要在 commit 说明里写清原因**。静默删除等于让下一个人再踩一遍。

**一句话**：修 bug 不是把拦路的代码拿掉，是**在它旁边补一条新的**。

---

## 数据与密钥安全（红线）

| # | 规则 | 反例 | 正确做法 |
|---|---|---|---|
| 1 | **接口不得返回服务器绝对路径** | `"path": "C:/Users/xxx/data/uploads/a.pdf"` | 只返回 `id`，取文件走 `GET /api/papers/{id}/file` |
| 2 | **代码里引用路径用相对路径** | `C:\Users\86180\Desktop\...` | `Path.of("uploads")` / `${UPLOAD_DIR:/data/uploads}` |
| 3 | **数据库密码不写死** | `spring.datasource.password=papermind_dev` | `${DB_PASSWORD:本地默认值}`，部署时用环境变量覆盖 |
| 4 | **API Key 走 .env** | 把 `sk-xxx` 写在代码或 properties 里 | `.env` 本地保存（已在 .gitignore），仓库只放 `.env.example` |
| 5 | **上传目录必须挂卷** | 容器内相对路径，重启即丢 | `docker-compose.yml` 挂 `uploads:/data/uploads` |

**自查一句话**：这份文件如果明天公开，会不会暴露我的电脑路径、密码或密钥？会，就不能提交。