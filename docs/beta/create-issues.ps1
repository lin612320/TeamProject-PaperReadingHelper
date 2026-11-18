# 批量创建 Beta Issue 到 GitHub（幂等：已存在的标签/里程碑跳过，issue 不查重，运行一次即可）
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$repo = 'lin612320/TeamProject-PaperReadingHelper'
$root = 'C:\Users\86180\Desktop\软件工程\PaperMind'
$items = Get-Content (Join-Path $root 'docs/beta/issues.json') -Raw -Encoding UTF8 | ConvertFrom-Json

Write-Host ("待创建 issue: " + $items.Count)

# ---------- 1. 标签 ----------
$colors = @{
  'beta' = '5319e7'; 'frontend' = '1d76db'; 'backend' = '0e8a16'; 'ai' = 'fbca04'
  'data' = '006b75'; 'deploy' = 'bfd4f2'; 'test' = 'd93f0b'; 'docs' = 'c5def5'
  'p1' = 'b60205'; 'p2' = 'f9d0c4'
}
$want = @{}
foreach ($i in $items) { foreach ($l in $i.labels) { if (-not $want.ContainsKey($l)) { $want[$l] = $true } } }
$have = @{}
(gh label list --repo $repo --limit 200) | ForEach-Object { $n = ($_ -split "`t")[0]; if ($n) { $have[$n.Trim()] = $true } }
$created = 0
foreach ($l in $want.Keys) {
  if ($have.ContainsKey($l)) { continue }
  $c = if ($colors.ContainsKey($l)) { $colors[$l] } elseif ($l -like 'epic:*') { 'ededed' } else { 'ededed' }
  gh label create $l --repo $repo --color $c 2>&1 | Out-Null
  $created++
}
Write-Host "标签：新建 $created 个，已存在 $($want.Count - $created) 个"

# ---------- 2. 里程碑 ----------
$msDue = @{ 'Beta-W1' = '2026-11-22T23:59:59Z'; 'Beta-W2' = '2026-11-29T23:59:59Z'; 'Beta-W3' = '2026-12-06T23:59:59Z'; 'Beta-W4' = '2026-12-11T23:59:59Z' }
$msNum = @{}
$existingMs = gh api "repos/$repo/milestones?state=all&per_page=100" | ConvertFrom-Json
foreach ($m in $existingMs) { $msNum[$m.title] = $m.number }
foreach ($t in $msDue.Keys) {
  if ($msNum.ContainsKey($t)) { continue }
  $r = gh api "repos/$repo/milestones" -X POST -f "title=$t" -f "due_on=$($msDue[$t])" -f "description=Beta 迭代 $t（D21 2026-11-18 → D44 2026-12-11）" | ConvertFrom-Json
  $msNum[$t] = $r.number
  Write-Host "里程碑新建：$t => #$($r.number)"
}
Write-Host ("里程碑编号：" + (($msNum.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join ', '))

# ---------- 3. Issue ----------
$tmp = Join-Path $env:TEMP ("issue-" + [guid]::NewGuid().ToString('N') + ".json")
$map = @()
$fail = @()
foreach ($i in $items) {
  $payload = [ordered]@{
    title     = $i.title
    body      = $i.body
    assignees = @($i.assignee)
    labels    = @($i.labels)
    milestone = $msNum[$i.milestone]
  }
  $json = $payload | ConvertTo-Json -Depth 6 -Compress
  [System.IO.File]::WriteAllText($tmp, $json, (New-Object System.Text.UTF8Encoding($false)))
  try {
    $resp = gh api "repos/$repo/issues" -X POST --input $tmp | ConvertFrom-Json
    $map += [pscustomobject]@{ no = $i.no; issue = $resp.number; title = $i.title; assignee = $i.assignee; milestone = $i.milestone; url = $resp.html_url }
    Write-Host ("OK  #{0}  <- {1}  {2}" -f $resp.number, $i.no, $i.title)
  } catch {
    $fail += [pscustomobject]@{ no = $i.no; title = $i.title; err = "$_" }
    Write-Host ("FAIL {0} {1} :: {2}" -f $i.no, $i.title, "$_")
  }
  Start-Sleep -Milliseconds 350
}
Remove-Item $tmp -ErrorAction SilentlyContinue

# ---------- 4. 输出映射 ----------
$out = Join-Path $root 'docs/beta/issue-map.csv'
$map | Sort-Object no | Export-Csv -Path $out -NoTypeInformation -Encoding UTF8
Write-Host ("`n汇总：成功 {0} / 失败 {1}" -f $map.Count, $fail.Count)
Write-Host ("映射表：" + $out)
if ($fail.Count -gt 0) { $fail | ForEach-Object { Write-Host ("失败明细：" + $_.no + " " + $_.err) } }
