#Requires -Version 5.1
<#
.SYNOPSIS
    Windows C 盘安全清理脚本

.DESCRIPTION
    默认以【模拟模式】运行，只预览将被删除的内容，不实际删除任何文件。
    切换到实际执行模式需要显式传入 -Execute 参数，并在提示处二次确认。

.PARAMETER Execute
    开关参数。不加此参数 = 模拟模式（安全）；加上则进入实际删除模式（需二次确认）。

.PARAMETER SkipPrefetch
    跳过清理 Windows Prefetch 目录（默认清理）。

.PARAMETER SkipSoftwareDistribution
    跳过清理 Windows Update 残留（默认清理）。

.PARAMETER SkipBrowserCache
    跳过清理浏览器缓存（默认清理）。

.EXAMPLE
    # 模拟模式（只预览，绝不删除）
    .\Clean-CDrive.ps1

.EXAMPLE
    # 实际执行（会提示二次确认）
    .\Clean-CDrive.ps1 -Execute
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$Execute,
    [switch]$SkipPrefetch,
    [switch]$SkipSoftwareDistribution,
    [switch]$SkipBrowserCache
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'SilentlyContinue'

# ─────────────────────────────────────────────
#  颜色辅助函数
# ─────────────────────────────────────────────
function Write-Header  { param($msg) Write-Host "`n══════════════════════════════════════" -ForegroundColor Cyan
                         Write-Host "  $msg" -ForegroundColor Cyan
                         Write-Host "══════════════════════════════════════" -ForegroundColor Cyan }
function Write-Section { param($msg) Write-Host "`n▶ $msg" -ForegroundColor Yellow }
function Write-Found   { param($msg) Write-Host "    $msg" -ForegroundColor Gray }
function Write-Deleted { param($msg) Write-Host "  ✓ 已删除: $msg" -ForegroundColor Green }
function Write-Simulated { param($msg) Write-Host "  ~ [模拟] 将删除: $msg" -ForegroundColor DarkYellow }
function Write-Warning2 { param($msg) Write-Host "  ⚠ $msg" -ForegroundColor Red }

# ─────────────────────────────────────────────
#  格式化文件大小
# ─────────────────────────────────────────────
function Format-Size {
    param([long]$bytes)
    if ($bytes -ge 1GB) { return "{0:N2} GB" -f ($bytes / 1GB) }
    if ($bytes -ge 1MB) { return "{0:N2} MB" -f ($bytes / 1MB) }
    if ($bytes -ge 1KB) { return "{0:N2} KB" -f ($bytes / 1KB) }
    return "$bytes B"
}

# ─────────────────────────────────────────────
#  统计目录大小（返回字节数）
# ─────────────────────────────────────────────
function Get-DirSize {
    param([string]$path)
    if (-not (Test-Path $path)) { return 0 }
    (Get-ChildItem -Path $path -Recurse -Force |
        Where-Object { -not $_.PSIsContainer } |
        Measure-Object -Property Length -Sum).Sum
}

# ─────────────────────────────────────────────
#  删除目录内文件（保留目录本身）
# ─────────────────────────────────────────────
function Clear-Directory {
    param([string]$path, [string]$label)
    if (-not (Test-Path $path)) {
        Write-Found "路径不存在，跳过: $path"
        return 0
    }
    $items = Get-ChildItem -Path $path -Recurse -Force
    $size  = ($items | Where-Object { -not $_.PSIsContainer } |
              Measure-Object -Property Length -Sum).Sum
    if ($size -eq $null) { $size = 0 }

    Write-Found "发现 $($items.Count) 个对象，约 $(Format-Size $size)  ←  $path"

    if ($Execute) {
        Remove-Item -Path "$path\*" -Recurse -Force
        Write-Deleted $label
    } else {
        Write-Simulated $label
    }
    return $size
}

# ─────────────────────────────────────────────
#  主程序开始
# ─────────────────────────────────────────────
Write-Header "Windows C 盘清理脚本 v1.0"

$mode = if ($Execute) { "【实际执行模式】" } else { "【模拟模式 — 不会删除任何文件】" }
Write-Host "`n  运行模式: $mode" -ForegroundColor $(if ($Execute) { 'Red' } else { 'Green' })

# ── 二次确认（仅实际模式）────────────────────
if ($Execute) {
    Write-Warning2 "即将真实删除文件！此操作不可完全撤销。"
    $confirm = Read-Host "`n  请输入 YES（大写）以继续，其他任意键退出"
    if ($confirm -ne 'YES') {
        Write-Host "`n  已取消。" -ForegroundColor Green
        exit 0
    }
}

# ── 权限检查 ─────────────────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Warning2 "建议以管理员身份运行以清理系统目录。当前部分区域可能无法访问。"
}

$totalFreed = [long]0

# ═══════════════════════════════════════════
#  1. C 盘空间现状分析
# ═══════════════════════════════════════════
Write-Header "1. C 盘空间现状"
$drive = Get-PSDrive C
$used  = $drive.Used
$free  = $drive.Free
$total = $used + $free
Write-Host ("  总容量  : {0}" -f (Format-Size $total))
Write-Host ("  已使用  : {0} ({1:N1}%)" -f (Format-Size $used), ($used/$total*100))
Write-Host ("  可用空间: {0} ({1:N1}%)" -f (Format-Size $free), ($free/$total*100))

# ═══════════════════════════════════════════
#  2. 主要垃圾来源扫描（仅统计，不删除）
# ═══════════════════════════════════════════
Write-Header "2. 主要垃圾来源扫描"

$targets = [ordered]@{
    "用户 TEMP ($env:TEMP)"           = $env:TEMP
    "系统 Temp (C:\Windows\Temp)"     = "C:\Windows\Temp"
    "Windows Prefetch"                = "C:\Windows\Prefetch"
    "WU 残留 (SoftwareDistribution)"  = "C:\Windows\SoftwareDistribution\Download"
    "Chrome 缓存"                     = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache"
    "Edge 缓存"                       = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cache"
    "旧日志 (CBS)"                    = "C:\Windows\Logs\CBS"
}

foreach ($kv in $targets.GetEnumerator()) {
    $sz = Get-DirSize $kv.Value
    Write-Host ("  {0,-40} {1,10}" -f $kv.Key, (Format-Size $sz))
}

# ═══════════════════════════════════════════
#  3. 清理操作
# ═══════════════════════════════════════════
Write-Header "3. 清理操作"

# 3-A  用户临时文件
Write-Section "用户 TEMP 目录"
$totalFreed += Clear-Directory $env:TEMP "用户 Temp 文件"

# 3-B  系统临时文件
Write-Section "系统 Temp 目录"
$totalFreed += Clear-Directory "C:\Windows\Temp" "系统 Temp 文件"

# 3-C  回收站
Write-Section "回收站"
$shellApp = New-Object -ComObject Shell.Application
$recycleBin = $shellApp.Namespace(0xA)
$rbCount = $recycleBin.Items().Count
Write-Found "回收站内共 $rbCount 个对象"
if ($Execute) {
    Clear-RecycleBin -Force -DriveLetter C
    Write-Deleted "回收站已清空"
} else {
    Write-Simulated "清空回收站（$rbCount 个对象）"
}

# 3-D  Windows Prefetch
if (-not $SkipPrefetch) {
    Write-Section "Windows Prefetch"
    $totalFreed += Clear-Directory "C:\Windows\Prefetch" "Prefetch 文件"
}

# 3-E  Windows Update 残留
if (-not $SkipSoftwareDistribution) {
    Write-Section "Windows Update 下载残留"
    Write-Warning2 "清理前将停止 wuauserv 服务，清理后自动启动"
    if ($Execute) {
        Stop-Service -Name wuauserv -Force
        $totalFreed += Clear-Directory "C:\Windows\SoftwareDistribution\Download" "WU Download"
        Start-Service -Name wuauserv
    } else {
        $totalFreed += Clear-Directory "C:\Windows\SoftwareDistribution\Download" "WU Download"
    }
}

# 3-F  浏览器缓存
if (-not $SkipBrowserCache) {
    Write-Section "浏览器缓存"
    $chromePath = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cache"
    $edgePath   = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cache"
    Write-Warning2 "请先关闭 Chrome 和 Edge 浏览器，否则部分文件可能无法删除"
    $totalFreed += Clear-Directory $chromePath "Chrome 缓存"
    $totalFreed += Clear-Directory $edgePath   "Edge 缓存"
}

# 3-G  旧日志
Write-Section "CBS 日志文件"
$totalFreed += Clear-Directory "C:\Windows\Logs\CBS" "CBS 日志"

# ═══════════════════════════════════════════
#  4. 汇总
# ═══════════════════════════════════════════
Write-Header "4. 汇总"
$verb = if ($Execute) { "已释放" } else { "预计可释放（模拟）" }
Write-Host ("  $verb 空间合计: {0}" -f (Format-Size $totalFreed)) -ForegroundColor Cyan

if (-not $Execute) {
    Write-Host @"

  ──────────────────────────────────────────────
  ★ 以上为【模拟预览】，未删除任何文件。
  ★ 确认无误后，以管理员身份运行以下命令执行实际清理：

      PowerShell -ExecutionPolicy Bypass -File ".\Clean-CDrive.ps1" -Execute

  ──────────────────────────────────────────────
"@ -ForegroundColor Green
}

Write-Host "`n  ⚠ 安全提示：" -ForegroundColor Red
Write-Host "    • 本脚本【不会】触碰用户文档、桌面、下载文件夹" -ForegroundColor Red
Write-Host "    • 本脚本【不会】修改注册表或系统配置" -ForegroundColor Red
Write-Host "    • Prefetch 清理后首次开机启动会略慢（正常现象）" -ForegroundColor Red
Write-Host "    • 建议清理前手动备份重要数据" -ForegroundColor Red
