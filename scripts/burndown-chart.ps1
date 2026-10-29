<#
.SYNOPSIS
    把燃尽图 CSV 画成 PNG（理想线 + 实际线），可直接在 GitHub 网页查看。

.EXAMPLE
    .\burndown-chart.ps1

.EXAMPLE
    .\burndown-chart.ps1 -Csv ..\docs\燃尽图\燃尽图模板.csv -Out ..\docs\燃尽图\燃尽图-当前.png
#>
[CmdletBinding()]
param(
    [string] $Csv = (Join-Path $PSScriptRoot '..\docs\燃尽图\燃尽图模板.csv'),
    [string] $Out = (Join-Path $PSScriptRoot '..\docs\燃尽图\燃尽图-当前.png'),
    [string] $Title = 'Alpha 冲刺燃尽图'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

if (-not (Test-Path $Csv)) { Write-Host "❌ 找不到 CSV：$Csv" -ForegroundColor Red; exit 1 }

$rows = @(Import-Csv -Path $Csv -Encoding UTF8)
if ($rows.Count -eq 0) { Write-Host '❌ CSV 为空' -ForegroundColor Red; exit 1 }

# ---------------- 数据整理 ----------------
$points = @()
for ($i = 0; $i -lt $rows.Count; $i++) {
    $r = $rows[$i]
    $dayNum = 0
    if ($r.'工作日' -match '(\d+)') { $dayNum = [int]$matches[1] }
    $ideal = 0
    if (-not [string]::IsNullOrWhiteSpace($r.'理想剩余Issue')) { $ideal = [double]$r.'理想剩余Issue' }
    $actual = $null
    if (-not [string]::IsNullOrWhiteSpace($r.'实际剩余Issue')) { $actual = [double]$r.'实际剩余Issue' }
    $points += [pscustomobject]@{ Day = $dayNum; Label = $r.'工作日'; Ideal = $ideal; Actual = $actual }
}

$maxY = ($points | ForEach-Object { $_.Ideal } | Measure-Object -Maximum).Maximum
$actualMax = ($points | Where-Object { $null -ne $_.Actual } | ForEach-Object { $_.Actual } | Measure-Object -Maximum).Maximum
if ($actualMax -gt $maxY) { $maxY = $actualMax }
$maxY = [math]::Ceiling($maxY / 4) * 4 + 4
if ($maxY -le 0) { $maxY = 32 }

# ---------------- 画布 ----------------
$W = 980; $H = 560
$bmp = New-Object System.Drawing.Bitmap $W, $H
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit

$bg = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(250,250,252))
$g.FillRectangle($bg, 0, 0, $W, $H)

$cBorder = ([System.Drawing.Color]::FromArgb(200,200,208))
$cGrid   = ([System.Drawing.Color]::FromArgb(228,228,235))
$cIdeal  = ([System.Drawing.Color]::FromArgb(150,150,160))
$cActual = ([System.Drawing.Color]::FromArgb(40,110,220))
$cText   = ([System.Drawing.Color]::FromArgb(60,60,70))

$titleFont = New-Object System.Drawing.Font 'Microsoft YaHei', 16, ([System.Drawing.FontStyle]::Bold)
$font      = New-Object System.Drawing.Font 'Microsoft YaHei', 10
$smallFont = New-Object System.Drawing.Font 'Microsoft YaHei', 9

$mL = 70; $mR = 40; $mT = 96; $mB = 84
$plotW = $W - $mL - $mR
$plotH = $H - $mT - $mB

$maxDay = ($points | ForEach-Object { $_.Day } | Measure-Object -Maximum).Maximum
if ($maxDay -le 0) { $maxDay = 15 }

function X($d) { return $mL + ($d / $maxDay) * $plotW }
function Y($v) { return $mT + $plotH - ($v / $maxY) * $plotH }

# 标题
$g.DrawString($Title, $titleFont, (New-Object System.Drawing.SolidBrush $cText), $mL, 18)

# 网格与 Y 轴刻度
$gridPen = New-Object System.Drawing.Pen $cGrid, 1
$step = [math]::Max(2, [math]::Round($maxY / 7))
for ($v = 0; $v -le $maxY; $v += $step) {
    $y = Y $v
    $g.DrawLine($gridPen, $mL, $y, $mL + $plotW, $y)
    $s = [string]$v
    $sz = $g.MeasureString($s, $smallFont)
    $g.DrawString($s, $smallFont, (New-Object System.Drawing.SolidBrush $cIdeal), $mL - $sz.Width - 8, $y - $sz.Height / 2)
}
# X 轴标签
foreach ($p in $points) {
    $x = X $p.Day
    $sz = $g.MeasureString($p.Label, $smallFont)
    $g.DrawString($p.Label, $smallFont, (New-Object System.Drawing.SolidBrush $cIdeal), $x - $sz.Width / 2, $mT + $plotH + 10)
}
# 坐标轴
$axisPen = New-Object System.Drawing.Pen $cBorder, 1.5
$g.DrawLine($axisPen, $mL, $mT, $mL, $mT + $plotH)
$g.DrawLine($axisPen, $mL, $mT + $plotH, $mL + $plotW, $mT + $plotH)

# 理想线（灰虚线）
$idealPen = New-Object System.Drawing.Pen $cIdeal, 2
$idealPen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
$prev = $null
foreach ($p in $points) {
    if ($null -eq $prev) { $prev = $p; continue }
    $g.DrawLine($idealPen, (X $prev.Day), (Y $prev.Ideal), (X $p.Day), (Y $p.Ideal))
    $prev = $p
}

# 实际线（蓝实线）—— 只在有数据的相邻点之间连线
$actualPen = New-Object System.Drawing.Pen $cActual, 3
$dotBrush = New-Object System.Drawing.SolidBrush $cActual
$prevA = $null
foreach ($p in $points) {
    if ($null -eq $p.Actual) { $prevA = $null; continue }
    if ($null -ne $prevA -and ($p.Day - $prevA.Day) -eq 1) {
        $g.DrawLine($actualPen, (X $prevA.Day), (Y $prevA.Actual), (X $p.Day), (Y $p.Actual))
    }
    $g.FillEllipse($dotBrush, (X $p.Day) - 4, (Y $p.Actual) - 4, 8, 8)
    $prevA = $p
}

# 图例
$lx = $mL + 10; $ly = $mT - 28
$g.DrawLine($idealPen, $lx, $ly + 6, $lx + 30, $ly + 6)
$g.DrawString('理想剩余', $font, (New-Object System.Drawing.SolidBrush $cIdeal), $lx + 36, $ly - 2)
$g.DrawLine($actualPen, $lx + 200, $ly + 6, $lx + 230, $ly + 6)
$g.DrawString('实际剩余', $font, (New-Object System.Drawing.SolidBrush $cActual), $lx + 236, $ly - 2)

# 右下角状态
$filled = @($points | Where-Object { $null -ne $_.Actual })
if ($filled.Count -gt 0) {
    $last = $filled[-1]
    $dev = $last.Actual - $last.Ideal
    $state = '正常'
    $stateColor = ([System.Drawing.Color]::FromArgb(30,140,60))
    if ($dev -ge 5) { $state = '严重落后，建议砍范围'; $stateColor = ([System.Drawing.Color]::FromArgb(200,40,40)) }
    elseif ($dev -ge 3) { $state = '落后，需处理阻塞'; $stateColor = ([System.Drawing.Color]::FromArgb(210,130,20)) }
    elseif ($dev -le -1) { $state = '领先理想线'; $stateColor = ([System.Drawing.Color]::FromArgb(30,140,60)) }
    $info = "{0}：实际 {1}，理想 {2}，偏差 {3:+#;-#;0}  —— {4}" -f $last.Label, $last.Actual, $last.Ideal, $dev, $state
    $g.DrawString($info, $font, (New-Object System.Drawing.SolidBrush $stateColor), $mL, $mT + $plotH + 34)
}
$g.DrawString(("生成时间 " + (Get-Date -Format 'yyyy-MM-dd HH:mm')), $smallFont, (New-Object System.Drawing.SolidBrush $cIdeal), $mL, $H - 26)

$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()

Write-Host "✅ 已生成 $Out" -ForegroundColor Green
