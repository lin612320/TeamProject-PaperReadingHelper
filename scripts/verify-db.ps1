<#
.SYNOPSIS
    验证本地 Docker 环境与数据库是否真的可用（Issue #2 / #21 的验收脚本）。

.DESCRIPTION
    做五件事：
      1. 起容器：docker compose up -d
      2. 等 postgres / redis 变成 healthy
      3. 查四张表是否都建出来了
      4. 查 pgvector 扩展是否装上
      5. 验级联删除、CHECK 约束是否真的生效

    输出可直接贴进 Issue #2 / #21 作为验收证据。

.EXAMPLE
    cd PaperMind
    .\scripts\verify-db.ps1
#>
[CmdletBinding()]
param(
    [int] $WaitSeconds = 90,
    [string] $ReportPath = ''
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Line($t) { Write-Host "" ; Write-Host ("=" * 70) ; Write-Host $t ; Write-Host ("=" * 70) }
function Ok($t)   { Write-Host "  [OK]   $t" -ForegroundColor Green }
function Bad($t)  { Write-Host "  [FAIL] $t" -ForegroundColor Red }
function Info($t) { Write-Host "  [..]   $t" -ForegroundColor Cyan }

$lines = New-Object System.Collections.Generic.List[string]
function Rec($t) { $lines.Add($t) | Out-Null; Write-Host $t }

Rec ("验证时间：" + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
Rec ("工作目录：" + $root)

# ---------------------------------------------------------------- 1. docker 可用
Line "1 / 5  检查 docker 是否可用"
$dv = (docker version --format '{{.Server.Version}}' 2>&1) | Out-String
if ($LASTEXITCODE -ne 0) {
    Bad "Docker 引擎未运行。请先打开 Docker Desktop，等鲸鱼图标稳定后重跑本脚本。"
    Rec "docker version 输出：$dv"
    if ($ReportPath) { $lines | Out-File -FilePath $ReportPath -Encoding UTF8 }
    exit 1
}
Ok ("Docker 引擎版本：" + $dv.Trim())
Rec ("Docker 引擎版本：" + $dv.Trim())

# ---------------------------------------------------------------- 2. 起容器
Line "2 / 5  启动容器（docker compose up -d）"
docker compose up -d 2>&1 | ForEach-Object { Rec ("    " + $_) }

Line "   等待 healthy（最多 $WaitSeconds 秒）"
$deadline = (Get-Date).AddSeconds($WaitSeconds)
$allHealthy = $false
while ((Get-Date) -lt $deadline) {
    $ps = (docker compose ps --format '{{.Name}}|{{.Status}}' 2>&1) | Out-String
    $hasPg = $ps -match 'papermind-postgres.*healthy'
    $hasRedis = $ps -match 'papermind-redis.*healthy'
    if ($hasPg -and $hasRedis) { $allHealthy = $true; break }
    Start-Sleep -Seconds 3
}

$psOut = (docker compose ps 2>&1) | Out-String
Rec ""
Rec $psOut

if ($allHealthy) { Ok "postgres 与 redis 均 healthy" ; Rec "结论：postgres 与 redis 均 healthy" }
else { Bad "未在 $WaitSeconds 秒内变成 healthy，见上面的 docker compose ps" ; Rec "结论：未在时限内 healthy" }

# ---------------------------------------------------------------- 3. 四张表
Line "3 / 5  检查四张表"
$tables = (docker exec papermind-postgres psql -U papermind -d papermind -t -c "\dt" 2>&1) | Out-String
Rec $tables
$required = 'papers', 'chunks', 'reading_session', 'annotation'
foreach ($t in $required) {
    if ($tables -match $t) { Ok ("表存在：" + $t) ; Rec ("表存在：" + $t) }
    else { Bad ("表缺失：" + $t) ; Rec ("表缺失：" + $t) }
}

# ---------------------------------------------------------------- 4. pgvector
Line "4 / 5  检查 pgvector 扩展"
$ext = (docker exec papermind-postgres psql -U papermind -d papermind -t -c "SELECT extname FROM pg_extension WHERE extname='vector'" 2>&1) | Out-String
if ($ext -match 'vector') { Ok "pgvector 扩展已安装" ; Rec "pgvector 扩展已安装" }
else { Bad "pgvector 扩展未安装" ; Rec "pgvector 扩展未安装：$ext" }

$dim = (docker exec papermind-postgres psql -U papermind -d papermind -t -c "SELECT format_type(atttypid, atttypmod) FROM pg_attribute WHERE attrelid='chunks'::regclass AND attname='embedding'" 2>&1) | Out-String
Rec ("embedding 列类型：" + $dim.Trim())

# ---------------------------------------------------------------- 5. 约束验证
Line "5 / 5  验证级联删除与 CHECK 约束"

$sql1 = "INSERT INTO papers (title, filename, file_path) VALUES ('__verify__','v.pdf','/tmp/v.pdf') RETURNING id;"
$newId = (docker exec papermind-postgres psql -U papermind -d papermind -t -c $sql1 2>&1) | Out-String
$newId = ($newId -replace '[^0-9]', '')
Rec ("插入测试论文 id=" + $newId)

if ($newId) {
    docker exec papermind-postgres psql -U papermind -d papermind -c "INSERT INTO chunks (paper_id, chunk_index, page, content) VALUES ($newId, 0, 1, 'x')" 2>&1 | Out-Null
    docker exec papermind-postgres psql -U papermind -d papermind -c "DELETE FROM papers WHERE id=$newId" 2>&1 | Out-Null
    $cnt = (docker exec papermind-postgres psql -U papermind -d papermind -t -c "SELECT count(*) FROM chunks WHERE paper_id=$newId" 2>&1) | Out-String
    $cnt = ($cnt -replace '[^0-9]', '')
    if ($cnt -eq '0') { Ok "级联删除生效（删论文后 chunks 已归零）" ; Rec "级联删除：生效" }
    else { Bad ("级联删除未生效，残留 " + $cnt + " 条 chunks") ; Rec ("级联删除：未生效，残留 $cnt") }
}

$bad = (docker exec papermind-postgres psql -U papermind -d papermind -c "UPDATE papers SET parse_status='done' WHERE id=1" 2>&1) | Out-String
if ($bad -match 'violates check constraint|错误|ERROR') { Ok "CHECK 约束生效（非法状态被拒绝）" ; Rec "CHECK 约束：生效" }
else { Bad "CHECK 约束未生效（非法值 done 竟然写入成功）" ; Rec "CHECK 约束：未生效" }

# ---------------------------------------------------------------- 汇总
Line "汇总"
$fails = ($lines | Select-String '缺失|未生效|未安装|FAIL' | Measure-Object).Count
if ($fails -eq 0) {
    Write-Host "  全部通过，可以把上面的输出贴进 Issue #2 和 #21" -ForegroundColor Green
    Rec "总体结论：全部通过"
} else {
    Write-Host "  有 $fails 项未通过，见上面标记 FAIL / 缺失 的行" -ForegroundColor Yellow
    Rec "总体结论：有 $fails 项未通过"
}

if ($ReportPath) {
    $lines | Out-File -FilePath $ReportPath -Encoding UTF8
    Write-Host ("  报告已写入：" + $ReportPath) -ForegroundColor Cyan
}
