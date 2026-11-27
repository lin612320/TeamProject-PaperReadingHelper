# scripts · 辅助脚本

> 所有脚本为 Windows PowerShell 5.1 兼容（本机默认环境），文件编码 UTF-8 BOM。
> ⚠️ 若你用编辑器改过这些 `.ps1` 并保存成「UTF-8 无 BOM」，PowerShell 5.1 会把中文读成乱码并报语法错误 —— 保存时必须带 BOM。

---

## start-papermind.ps1 / .cmd · 一键启动（2026-11-24 起）

起 Docker、等容器 healthy、自检数据库与接口，一条命令走完。**入口只有一份，在仓库里**；桌面上的 `start-papermind.cmd` 是转发到这里的薄壳。

```powershell
cd PaperMind

.\scripts\start-papermind.cmd              # 默认：起服务 + 自检
.\scripts\start-papermind.cmd -Build       # 代码改了才需要，重建镜像（2-5 分钟）
.\scripts\start-papermind.cmd -Status      # 只看状态，不动容器
.\scripts\start-papermind.cmd -Down        # 停容器，数据卷保留
.\scripts\start-papermind.cmd -Logs        # 跟后端日志，Ctrl+C 退出不影响容器
```

它做的五件事，失败时都会停在那一步并给出下一步提示：

| 步骤 | 做什么 | 为什么要有 |
|---|---|---|
| 1 | Docker Desktop 没跑就拉起来，轮询等引擎就绪（默认最多 300s） | 手动点图标再等，每天浪费一分钟 |
| 2 | `docker compose up -d`（`-Build` 时加 `--build`） | 统一入口，避免有人用 `run` 绕开健康检查 |
| 3 | 等 5 个容器全部 healthy | `Up` 不等于能用，模型没加载完问答会 3001 |
| 4 | 自检 `users` 表，缺了自动补跑 `migrate-users-1.1.0.sql` | **BUG-028 的教训**：`03-数据库表结构.sql` 只在空数据目录时执行，存量库永远缺表，注册/登录会 500 |
| 5 | 探活 8081 / 8080 / 8000 | 起来但接口 500 的情况比你想的多 |

参数：`-Repo <path>`（默认取脚本上级目录）、`-TimeoutSeconds <n>`（默认 300）。

> 历史坑：这个脚本原先只存在于桌面、没进 git，某次清理被删掉后桌面 `.cmd` 成了死链，谁都没发现。所以现在真身放进 `scripts/`，桌面只留薄壳。

---

## burndown.ps1 · 燃尽图自动统计

统计 GitHub 仓库的未关闭 Issue 数，写入 `docs/燃尽图/燃尽图模板.csv`，并算出当日完成数与偏差。

### 三种取值方式（按顺序自动选择）

| 方式 | 命令 | 适用 |
|---|---|---|
| **手动**（最可靠，离线可用） | `.\burndown.ps1 -Remaining 24` | 每天例会后数一下还剩几条 |
| **gh CLI 自动** | `gh auth login` 后 `.\burndown.ps1` | 已登录 gh 的机器 |
| **REST API 自动** | `$env:GITHUB_TOKEN='ghp_xxx'; .\burndown.ps1 -Proxy http://127.0.0.1:10090` | 只有 PAT，或需要代理 |

### 常用参数

| 参数 | 说明 | 默认 |
|---|---|---|
| `-Remaining <N>` | 手动指定今天的剩余 Issue 数 | 自动查询 |
| `-Day <D5>` | 补录或改某一天 | 第一个未填的行 |
| `-Total <N>` | 手动指定 Issue 总数 | open + closed |
| `-Proxy <url>` | REST API 走代理 | 无 |
| `-DryRun` | 只打印不写文件 | 关 |

### 典型用法

```powershell
cd PaperMind

# 每天例会后（最常用）
.\scripts\burndown.ps1 -Remaining 24

# 全自动
.\scripts\burndown.ps1

# 补录第 5 天
.\scripts\burndown.ps1 -Day D5 -Remaining 19

# 先看看会发生什么，不写文件
.\scripts\burndown.ps1 -Remaining 24 -DryRun
```

### 脚本会做什么

1. 首次运行自动把 **D0 基线**填成当前 Issue 总数（备注标注「基线（脚本自动填入）」）
2. 找到当天该填的行（或 `-Day` 指定的行）
3. 计算 `当日完成数`、`当日新增数`、`累计完成`
4. 与「理想剩余Issue」比较，提示领先/落后几条
5. 回写 CSV（保留理想列，UTF-8 BOM，Excel 打开不乱码）
6. 控制台打印迷你燃尽图：

```
  迷你燃尽图（█ 实际  · 理想）
  D0   ████████████████████████████ 28
  D1   ████████████████████████████ 28
  D2   █████████████████████████ 25
```

### 已有 Issue、但数量是 0？

说明仓库里还没建 Issue。两种做法：

1. 手动在 GitHub 上照 `docs/alpha/Alpha_Issue清单.md` 建 28 条
2. 或者继续用 `-Remaining` 手动记录（燃尽图照样能画，只是不与 Issue 联动）

### 拍图流程

```powershell
# 1. 每天记录
.\scripts\burndown.ps1 -Remaining 24

# 2. CSV 里填满后，用 Excel 打开 → 选中三列 → 插入折线图 → 截图
#    docs/燃尽图/燃尽图-第6周.png / 燃尽图-第7周.png
```

详见 [`../docs/燃尽图/README.md`](../docs/燃尽图/README.md)。

---

## burndown-chart.ps1 · 生成燃尽可能图表

把 CSV 画成 PNG（灰色虚线=理想，蓝色实线=实际），生成后可在 GitHub 网页直接看。

``powershell
# 默认输出 docs/燃尽图/燃尽图-当前.png
.\scripts\burndown-chart.ps1

# 出里程碑图（博客用）
.\scripts\burndown-chart.ps1 -Out ..\docs\燃尽图\燃尽图-第6周.png -Title 'Alpha 冲刺燃尽图（第 6 周）'
``

| 参数 | 说明 | 默认 |
|---|---|---|
| -Csv | 数据源 | docs/燃尽图/燃尽图模板.csv |
| -Out | 输出 PNG | docs/燃尽图/燃尽图-当前.png |
| -Title | 图标题 | Alpha 冲刺燃尽图 |

依赖 Windows 自带的 System.Drawing，无需安装任何东西。
查看入口：[../docs/燃尽图/燃尽图-当前.md](../docs/燃尽图/燃尽图-当前.md)

---

## verify-db.ps1 · 环境与数据库验收

一条命令验完 Issue #2 和 #21 的全部验收点，输出可直接贴进 Issue 当证据。

````powershell
cd PaperMind
.\scripts\verify-db.ps1
.\scripts\verify-db.ps1 -ReportPath ..\docs\例会\2026-10-28\环境验证.txt
````

做五件事：
1. 检查 Docker 引擎是否在跑
2. `docker compose up -d` 并等待 postgres / redis 变成 healthy
3. 查四张表（papers / chunks / reading_session / annotation）是否都建出来
4. 查 pgvector 扩展与 `chunks.embedding` 的维度
5. 验级联删除、CHECK 约束是否真的生效