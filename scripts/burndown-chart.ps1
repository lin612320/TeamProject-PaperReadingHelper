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
    $ideal = $null
    if (-not [string]::IsNullOrWhiteSpace($r.'理想剩余Issue')) { $ideal = [double]$r.'理想剩余Issue' }
    $oldIdeal = $null
    if ($r.PSObject.Properties.Name -contains '旧基线理想' -and -not [string]::IsNullOrWhiteSpace($r.'旧基线理想')) { $oldIdeal = [double]$r.'旧基线理想' }
    $actual = $null
    if (-not [string]::IsNullOrWhiteSpace($r.'实际剩余Issue')) { $actual = [double]$r.'实际剩余Issue' }
    $added = 0
    if (-not [string]::IsNullOrWhiteSpace($r.'当日新增数')) { $added = [int]$r.'当日新增数' }
    $points += [pscustomobject]@{ Day = $dayNum; Label = $r.'工作日'; Ideal = $ideal; OldIdeal = $oldIdeal; Actual = $actual; Added = $added }
}

$maxY = ($points | ForEach-Object { $_.Ideal; $_.OldIdeal } | Where-Object { $null -ne $_ } | Measure-Object -Maximum).Maximum
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

# 旧基线理想线（浅灰点线）—— scope 变更前的原计划，只作历史对照
$cOldIdeal = ([System.Drawing.Color]::FromArgb(203,203,213))
$oldIdealPen = New-Object System.Drawing.Pen $cOldIdeal, 1.5
$oldIdealPen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dot
$prevO = $null
foreach ($p in $points) {
    if ($null -eq $p.OldIdeal) { $prevO = $null; continue }
    if ($null -ne $prevO -and ($p.Day - $prevO.Day) -eq 1) {
        $g.DrawLine($oldIdealPen, (X $prevO.Day), (Y $prevO.OldIdeal), (X $p.Day), (Y $p.OldIdeal))
    }
    $prevO = $p
}

# 新基线理想线（灰虚线）—— scope 变更后重新排的计划，从变更点起算到 D18=0
$idealPen = New-Object System.Drawing.Pen $cIdeal, 2
$idealPen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
$prev = $null
foreach ($p in $points) {
    if ($null -eq $p.Ideal) { $prev = $null; continue }
    if ($null -ne $prev -and ($p.Day - $prev.Day) -eq 1) {
        $g.DrawLine($idealPen, (X $prev.Day), (Y $prev.Ideal), (X $p.Day), (Y $p.Ideal))
    }
    $prev = $p
}

# scope 变更竖线（标在新基线起点）
$firstNew = $points | Where-Object { $null -ne $_.Ideal } | Select-Object -First 1
if ($null -ne $firstNew) {
    $vx = X $firstNew.Day
    $cMark = ([System.Drawing.Color]::FromArgb(185,140,30))
    $vPen = New-Object System.Drawing.Pen $cMark, 1.5
    $vPen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
    $g.DrawLine($vPen, $vx, $mT, $vx, $mT + $plotH)
    $lbl = 'scope 变更 +11'
    $szl = $g.MeasureString($lbl, $smallFont)
    $g.DrawString($lbl, $smallFont, (New-Object System.Drawing.SolidBrush $cMark), [math]::Max($mL + 2, $vx - $szl.Width - 6), $mT + 4)
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
$g.DrawString('理想（新基线）', $font, (New-Object System.Drawing.SolidBrush $cIdeal), $lx + 36, $ly - 2)
$g.DrawLine($oldIdealPen, $lx + 190, $ly + 6, $lx + 220, $ly + 6)
$g.DrawString('旧基线（scope 变更前）', $smallFont, (New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(175,175,188))), $lx + 226, $ly)
$g.DrawLine($actualPen, $lx + 400, $ly + 6, $lx + 430, $ly + 6)
$g.DrawString('实际剩余', $font, (New-Object System.Drawing.SolidBrush $cActual), $lx + 436, $ly - 2)

# 右下角状态
$filled = @($points | Where-Object { $null -ne $_.Actual })
if ($filled.Count -gt 0) {
    $last = $filled[-1]
    $lastIdeal = 0
    if ($null -ne $last.Ideal) { $lastIdeal = $last.Ideal }
    $dev = $last.Actual - $lastIdeal
    $state = '正常'
    $stateColor = ([System.Drawing.Color]::FromArgb(30,140,60))
    if ($last.Added -gt 0) {
        # 范围变更：当日新增了 Issue（如被要求扩范围），此处的正向偏差不是落后，不能按落后打分
        $state = "当日 scope 变更（新增 $($last.Added) 条），已按新基线重设理想线"
        $stateColor = ([System.Drawing.Color]::FromArgb(90,90,160))
    }
    elseif ($dev -ge 5) { $state = '严重落后，建议砍范围'; $stateColor = ([System.Drawing.Color]::FromArgb(200,40,40)) }
    elseif ($dev -ge 3) { $state = '落后，需处理阻塞'; $stateColor = ([System.Drawing.Color]::FromArgb(210,130,20)) }
    elseif ($dev -le -1) { $state = '领先理想线'; $stateColor = ([System.Drawing.Color]::FromArgb(30,140,60)) }
    $info = "{0}：实际 {1}，新基线理想 {2}，偏差 {3:+#;-#;0}  —— {4}" -f $last.Label, $last.Actual, $lastIdeal, $dev, $state
    $g.DrawString($info, $font, (New-Object System.Drawing.SolidBrush $stateColor), $mL, $mT + $plotH + 24)
}
$g.DrawString('说明：纵轴仅统计未关闭 Issue；BugList 中的缺陷（BUG-012 / BUG-013 / BUG-016 等）另行跟踪，未计入本图', $smallFont, (New-Object System.Drawing.SolidBrush $cIdeal), $mL, $H - 38)
$g.DrawString(("生成时间 " + (Get-Date -Format 'yyyy-MM-dd HH:mm')), $smallFont, (New-Object System.Drawing.SolidBrush $cIdeal), $mL, $H - 18)

$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()

Write-Host "✅ 已生成 $Out" -ForegroundColor Green
