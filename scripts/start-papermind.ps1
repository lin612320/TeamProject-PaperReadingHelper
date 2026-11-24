<#
.SYNOPSIS
    PaperMind 一键启动（Windows / PowerShell 5.1）

.DESCRIPTION
    做四件事，每件都可单独跑：
      1. 确认 Docker Desktop 在跑（没跑就拉起来，并等引擎就绪）
      2. docker compose up -d 起 5 个容器
      3. 等 5 个容器变 healthy
      4. 自检：users 表在不在（不在就补跑幂等迁移）、后端接口通不通

.EXAMPLE
    .\start-papermind.ps1
    默认：起服务 + 自检

.EXAMPLE
    .\start-papermind.ps1 -Build
    代码改了才需要：重建镜像后起服务

.EXAMPLE
    .\start-papermind.ps1 -Status
    只看状态，不动任何容器

.EXAMPLE
    .\start-papermind.ps1 -Down
    停容器，数据卷保留

.EXAMPLE
    .\start-papermind.ps1 -Logs
    跟后端日志（Ctrl+C 退出，不影响容器）
#>
[CmdletBinding()]
param(
    [switch] $Build,
    [switch] $Down,
    [switch] $Status,
    [switch] $Logs,
    [string] $Repo = (Split-Path $PSScriptRoot -Parent),
    [int]    $TimeoutSeconds = 300
)

$ErrorActionPreference = 'Continue'

function Step($m) { Write-Host "🔄 $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "✅ $m" -ForegroundColor Green }
function Warn($m) { Write-Host "⚠️  $m" -ForegroundColor Yellow }
function Err($m)  { Write-Host "❌ $m" -ForegroundColor Red }

# ---------------------------------------------------------------- 0. 前置检查
if (-not (Test-Path $Repo)) {
    Err "找不到项目目录：$Repo"
    Write-Host "   用 -Repo 指定 PaperMind 的实际路径" -ForegroundColor Gray
    exit 1
}
Set-Location $Repo
Ok "项目目录 $Repo"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Err "docker 命令不存在，请确认 Docker Desktop 已安装"
    exit 1
}

# ---------------------------------------------------------------- 1. 引擎
function Test-Engine {
    # 用 cmd 包一层：docker 往 stderr 写东西时不会把脚本打断
    cmd /c "docker info >nul 2>&1"
    return ($LASTEXITCODE -eq 0)
}

function Start-Engine {
    if (Test-Engine) { Ok 'Docker 引擎已在运行'; return $true }

    $exe = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path $exe)) {
        Err "没找到 Docker Desktop：$exe"
        return $false
    }

    Step 'Docker 引擎未运行，正在拉起 Docker Desktop（首次约 30-60 秒）'
    Start-Process $exe | Out-Null

    $waited = 0
    while ($waited -lt $TimeoutSeconds) {
        Start-Sleep -Seconds 5
        $waited += 5
        if (Test-Engine) { Ok "引擎就绪（等了 ${waited} 秒）"; return $true }
        Write-Host "   …等待引擎 ${waited}s" -ForegroundColor DarkGray
    }
    Err "等了 ${TimeoutSeconds} 秒引擎仍未就绪。手动开一下 Docker Desktop 再重试"
    return $false
}

# ---------------------------------------------------------------- -Status 分支
if ($Status) {
    Write-Host ''
    Step '容器状态'
    docker compose ps
    Write-Host ''
    Step '接口探活'
    foreach ($u in @('http://localhost:8081/','http://localhost:8080/api/papers')) {
        $code = (curl.exe -s -o NUL -w "%{http_code}" --max-time 10 $u)
        if ($code -eq '200') { Ok "$u  →  $code" } else { Warn "$u  →  $code" }
    }
    exit 0
}

# ---------------------------------------------------------------- -Logs 分支
if ($Logs) {
    Step '跟随后端日志（Ctrl+C 退出）'
    docker compose logs -f backend
    exit 0
}

if (-not (Start-Engine)) { exit 1 }

# ---------------------------------------------------------------- 2. 停
if ($Down) {
    Step '停止容器（数据卷保留，不会丢论文）'
    docker compose down
    Ok '已停止。下次启动直接跑本脚本即可'
    exit 0
}

# ---------------------------------------------------------------- 3. 起
if ($Build) {
    Step '重建镜像并启动（代码改动后才需要，约 2-5 分钟）'
    $upOut = docker compose up -d --build 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { Write-Host $upOut; Err '构建或启动失败，见上面输出'; exit 1 }
} else {
    Step '启动容器'
    # docker compose 会把进度写 stderr，直接输出会被 PS 5.1 当成 ErrorRecord 整段染红，先吞掉
    $upOut = docker compose up -d 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { Write-Host $upOut; Err '启动失败，见上面输出'; exit 1 }
}
Ok '容器已拉起'

# ---------------------------------------------------------------- 4. 等 healthy
Step '等待 5 个容器 healthy'
$want = @('papermind-postgres', 'papermind-redis', 'papermind-ai', 'papermind-backend', 'papermind-frontend')
$waited = 0
$allHealthy = $false
while ($waited -lt $TimeoutSeconds) {
    $lines = @(docker ps --format '{{.Names}}|{{.Status}}' 2>$null)
    $unhealthy = @()
    foreach ($n in $want) {
        $line = $lines | Where-Object { $_ -like "$n|*" } | Select-Object -First 1
        if (-not $line) { $unhealthy += "$n(未运行)"; continue }
        if ($line -notlike '*healthy*') { $unhealthy += $n }
    }
    if ($unhealthy.Count -eq 0) { $allHealthy = $true; break }
    Start-Sleep -Seconds 5
    $waited += 5
    if ($waited % 15 -eq 0) { Write-Host "   仍在等：$($unhealthy -join ', ')  (${waited}s)" -ForegroundColor DarkGray }
}

Write-Host ''
docker compose ps
Write-Host ''

if (-not $allHealthy) {
    Warn "等 ${TimeoutSeconds} 秒仍有容器未 healthy，最近日志："
    docker compose logs --tail 40 backend
    exit 1
}
Ok '5 个容器全部 healthy'

# ---------------------------------------------------------------- 5. 自检：users 表
# BUG-028 的教训：03-数据库表结构.sql 只在空数据目录时执行，
# 存量库必须单独跑一次迁移，否则注册/登录会 500。
Step '自检 users 表（多用户隔离的前置）'
$hasUsers = (docker compose exec -T postgres psql -U papermind -d papermind -tAc "select to_regclass('public.users') is not null;" 2>$null)
if ($hasUsers -match 't') {
    Ok 'users 表已存在，跳过迁移'
} else {
    Warn 'users 表不存在 → 补跑幂等迁移 scripts\migrate-users-1.1.0.sql'
    Get-Content (Join-Path $Repo 'scripts\migrate-users-1.1.0.sql') -Raw -Encoding UTF8 |
        docker compose exec -T postgres psql -U papermind -d papermind
    $hasUsers = (docker compose exec -T postgres psql -U papermind -d papermind -tAc "select to_regclass('public.users') is not null;" 2>$null)
    if ($hasUsers -match 't') { Ok '迁移完成，users 表已建' } else { Err '迁移失败，请手动检查'; exit 1 }
}

# ---------------------------------------------------------------- 6. 自检：接口
Step '接口探活'
$bad = 0
foreach ($u in @('http://localhost:8081/', 'http://localhost:8080/api/papers', 'http://localhost:8000/internal/health')) {
    $code = (curl.exe -s -o NUL -w "%{http_code}" --max-time 15 $u)
    if ($code -eq '200') { Ok "$u  →  $code" } else { Warn "$u  →  $code"; $bad++ }
}

Write-Host ''
Write-Host '============================================================' -ForegroundColor Cyan
if ($bad -eq 0) { Write-Host ' PaperMind 已就绪' -ForegroundColor Green }
else            { Write-Host " PaperMind 起来了，但有 $bad 个接口探活失败（见上）" -ForegroundColor Yellow }
Write-Host '============================================================' -ForegroundColor Cyan
Write-Host '  阅读页    http://localhost:8081'
Write-Host '  后端接口  http://localhost:8080/api'
Write-Host '  AI 服务   http://localhost:8000/internal/health'
Write-Host ''
Write-Host '  登录说明  当前 AUTH_ENFORCE=false，未带令牌按 legacy 用户（12 篇存量）'
Write-Host '            要试真实登录：注册后带浏览器令牌访问，或临时注入 AUTH_ENFORCE=true'
Write-Host ''
Write-Host '  看日志    .\start-papermind.cmd -Logs'
Write-Host '  看状态    .\start-papermind.cmd -Status'
Write-Host '  重建镜像  .\start-papermind.cmd -Build'
Write-Host '  停止      .\start-papermind.cmd -Down'
Write-Host '------------------------------------------------------------'
exit 0
