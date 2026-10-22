<#
.SYNOPSIS
    自动统计 GitHub Issues 剩余数并写入燃尽图 CSV。

.DESCRIPTION
    三种取值方式，按优先级自动选择：
      1. -Remaining <数字>   手动指定（离线也能用）
      2. gh CLI 已登录       自动统计 open issues（排除 PR）
      3. $env:GITHUB_TOKEN  走 REST API（可配 -Proxy）

    每天例会后跑一次，脚本会：
      - 首次运行时把 D0 基线填为当前 Issue 总数
      - 自动找到当天该填的行（也可用 -Day 指定）
      - 计算「当日完成 / 当日新增 / 累计完成」
      - 回写 CSV（保留理想剩余列，UTF-8 BOM，Excel 直接打开不乱码）

.EXAMPLE
    # 完全离线，手动填今天的剩余数
    .\burndown.ps1 -Remaining 24

.EXAMPLE
    # gh 已登录时全自动
    gh auth login
    .\burndown.ps1

.EXAMPLE
    # 用 PAT + 代理
    $env:GITHUB_TOKEN = 'ghp_xxxxxxxx'
    .\burndown.ps1 -Proxy http://127.0.0.1:10090

.EXAMPLE
    # 指定补录某一天
    .\burndown.ps1 -Day D5 -Remaining 19
#>
[CmdletBinding()]
param(
    [string] $Repo      = 'lin612320/TeamProject-PaperReadingHelper',
    [string] $Csv       = (Join-Path $PSScriptRoot '..\docs\燃尽图\燃尽图模板.csv'),
    [string] $Token     = $env:GITHUB_TOKEN,
    [string] $Proxy     = '',
    [string] $Day       = '',
    [int]    $Remaining = -1,
    [int]    $Total     = -1,
    [switch] $DryRun
)

$ErrorActionPreference = 'Stop'

function Write-Step($msg) { Write-Host "🔄 $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "✅ $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "⚠️  $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "❌ $msg" -ForegroundColor Red }

# ---------------------------------------------------------------- 取数
function Get-IssueStats {
    param([string] $Repo, [string] $Token, [string] $Proxy)

    $result = [pscustomobject]@{ Open = -1; Closed = -1; Source = '' }

    # 方式 2：gh CLI
    $gh = Get-Command gh -ErrorAction SilentlyContinue
    if ($gh) {
        $authed = $false
        try { gh auth status 2>&1 | Out-Null; $authed = ($LASTEXITCODE -eq 0) } catch { $authed = $false }
        if ($authed) {
            try {
                $openJson   = gh api "repos/$Repo/issues?state=open&per_page=100"   2>$null | ConvertFrom-Json
                $closedJson = gh api "repos/$Repo/issues?state=closed&per_page=100" 2>$null | ConvertFrom-Json
                $result.Open   = @($openJson   | Where-Object { -not $_.pull_request }).Count
                $result.Closed = @($closedJson | Where-Object { -not $_.pull_request }).Count
                $result.Source = 'gh CLI'
                return $result
            } catch {
                Write-Warn2 "gh CLI 查询失败，尝试 REST API：$($_.Exception.Message)"
            }
        } else {
            Write-Warn2 'gh 未登录，跳过（可先运行 gh auth login）'
        }
    }

    # 方式 3：REST API
    if ($Token) {
        $headers = @{
            Authorization          = "Bearer $Token"
            Accept                 = 'application/vnd.github+json'
            'X-GitHub-Api-Version' = '2022-11-28'
            'User-Agent'           = 'papermind-burndown'
        }
        $invoke = @{
            Headers    = $headers
            TimeoutSec = 30
        }
        if ($Proxy) { $invoke['Proxy'] = $Proxy }

        try {
            $open   = Invoke-RestMethod @invoke -Uri "https://api.github.com/repos/$Repo/issues?state=open&per_page=100"
            $closed = Invoke-RestMethod @invoke -Uri "https://api.github.com/repos/$Repo/issues?state=closed&per_page=100"
            $result.Open   = @($open   | Where-Object { -not $_.pull_request }).Count
            $result.Closed = @($closed | Where-Object { -not $_.pull_request }).Count
            $result.Source = 'REST API'
            return $result
        } catch {
            Write-Warn2 "REST API 失败：$($_.Exception.Message)"
        }
    }

    return $result
}

# ---------------------------------------------------------------- 主流程
Write-Step "读取燃尽表：$Csv"
if (-not (Test-Path $Csv)) { Write-Err "找不到 CSV：$Csv"; exit 1 }

$rows = @(Import-Csv -Path $Csv -Encoding UTF8)
if ($rows.Count -eq 0) { Write-Err 'CSV 为空'; exit 1 }

# 取数
$stats = [pscustomobject]@{ Open = -1; Closed = -1; Source = '' }
if ($Remaining -ge 0) {
    $stats.Open   = $Remaining
    $stats.Closed = -1
    $stats.Source = '手动指定 -Remaining'
} else {
    Write-Step '查询 GitHub Issues 数量…'
    $stats = Get-IssueStats -Repo $Repo -Token $Token -Proxy $Proxy
    if ($stats.Open -lt 0) {
        Write-Err '无法获取 Issue 数量。请用以下任一方式：'
        Write-Host '  1) gh auth login                             然后重跑' -ForegroundColor Gray
        Write-Host '  2) $env:GITHUB_TOKEN = "ghp_xxx"             然后重跑' -ForegroundColor Gray
        Write-Host '  3) .\burndown.ps1 -Remaining 24              手动填剩余数' -ForegroundColor Gray
        exit 1
    }
}

$openCount   = $stats.Open
$closedCount = $stats.Closed

# 总量：优先 -Total，其次 API 的 open+closed，最后取 D0 的值
if ($Total -ge 0) {
    $totalIssues = $Total
} elseif ($closedCount -ge 0) {
    $totalIssues = $openCount + $closedCount
} else {
    $totalIssues = [int]$rows[0].'理想剩余Issue'
}

Write-Host ""
Write-Host "  数据来源 : $($stats.Source)" -ForegroundColor Gray
Write-Host "  未关闭   : $openCount" -ForegroundColor Gray
Write-Host "  已关闭   : $(if ($closedCount -ge 0) { $closedCount } else { '未知' })" -ForegroundColor Gray
Write-Host "  Issue 总数: $totalIssues" -ForegroundColor Gray
Write-Host ""

if ($openCount -eq 0 -and $closedCount -le 0) {
    Write-Warn2 '仓库里还没有 Issue，先去 GitHub 建 Issue，或用 -Remaining 手动记录'
}

# D0 基线：第一次运行时补
if ([string]::IsNullOrWhiteSpace($rows[0].'实际剩余Issue')) {
    $rows[0].'实际剩余Issue' = [string]$openCount
    if ([string]::IsNullOrWhiteSpace($rows[0].'日期')) {
        $rows[0].'日期' = (Get-Date -Format 'yyyy-MM-dd')
    }
    $rows[0].'备注' = '基线（脚本自动填入）'
    Write-Ok "已补 D0 基线：剩余 $openCount"
}

# 定位目标行
if ($Day) {
    $target = $rows | Where-Object { $_.'工作日' -eq $Day } | Select-Object -First 1
    if (-not $target) { Write-Err "CSV 里没有 $Day 这一行"; exit 1 }
} else {
    $target = $rows | Where-Object { [string]::IsNullOrWhiteSpace($_.'实际剩余Issue') } | Select-Object -First 1
    if (-not $target) { Write-Err 'D1–D15 已全部填满，没有可写的行'; exit 1 }
}

# 上一行（用于算当日完成/新增）
$idx = [array]::IndexOf($rows, $target)
$prev = if ($idx -gt 0) { $rows[$idx - 1] } else { $null }
$prevRemaining = if ($prev -and -not [string]::IsNullOrWhiteSpace($prev.'实际剩余Issue')) { [int]$prev.'实际剩余Issue' } else { $totalIssues }
$prevDone      = $totalIssues - $prevRemaining

$doneToday = 0
if ($closedCount -ge 0) {
    $doneToday = $closedCount - $prevDone
} else {
    $doneToday = $prevRemaining - $openCount
}
$newToday  = $doneToday - ($prevRemaining - $openCount)

# 写回
$target.'日期'           = (Get-Date -Format 'yyyy-MM-dd')
$target.'实际剩余Issue'  = [string]$openCount
$target.'当日完成数'     = [string]$doneToday
$target.'当日新增数'     = [string]$newToday
$target.'累计完成'       = [string]($totalIssues - $openCount)

Write-Host "  写入行   : $($target.'工作日')  ($($target.'日期'))" -ForegroundColor Gray
Write-Host "  实际剩余 : $openCount    当日完成: $doneToday    当日新增: $newToday" -ForegroundColor Gray
Write-Host "  理想剩余 : $($target.'理想剩余Issue')" -ForegroundColor Gray

$deviation = $openCount - [int]$target.'理想剩余Issue'
if ($deviation -gt 0) {
    Write-Warn2 "落后理想线 $deviation 条"
} elseif ($deviation -lt 0) {
    Write-Ok "领先理想线 $([math]::Abs($deviation)) 条"
} else {
    Write-Ok '正好在理想线上'
}

if ($DryRun) {
    Write-Warn2 '-DryRun：不写文件'
} else {
    $rows | Export-Csv -Path $Csv -NoTypeInformation -Encoding UTF8
    Write-Ok "已更新 $Csv"
}

# 控制台迷你燃尽图
Write-Host ""
Write-Host '  迷你燃尽图（█ 实际  · 理想）' -ForegroundColor DarkGray
$maxBar = 28
foreach ($r in $rows) {
    if ([string]::IsNullOrWhiteSpace($r.'实际剩余Issue')) { continue }
    $v = [int]$r.'实际剩余Issue'
    $len = [math]::Max(0, [math]::Round($v / $maxBar * 28))
    $bar = '█' * $len
    $ideal = [int]$r.'理想剩余Issue'
    $gap = [math]::Max(0, [math]::Round($ideal / $maxBar * 28) - $len)
    Write-Host ("  {0,-4} {1}{2} {3}" -f $r.'工作日', $bar, ('·' * $gap), $v) -ForegroundColor $(if ($v -gt $ideal) { 'Yellow' } else { 'Green' })
}
