# ==============================================================================
# E-ZZIO V9.3 — Automated Visual Inspection & Proof Capture Tool
# Captures pixel-accurate screenshots of Desktop and Android runtimes.
# ==============================================================================
param (
    [string]$TargetDir = "state\audit\visual\v9.3\baseline",
    [string]$Port = "8001"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$FullTargetDir = Join-Path $RootDir $TargetDir

if (-not (Test-Path $FullTargetDir)) {
    New-Item -ItemType Directory -Force -Path $FullTargetDir | Out-Null
}

$BraveExe = "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
$AdbExe = "G:\tools\platform-tools\adb.exe"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   E-ZZIO V9.3 VISUAL CAPTURE ENGINE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[TARGET] Destination: $FullTargetDir" -ForegroundColor Gray

# 1. Desktop captures via Brave Headless
$BaseUrl = "http://127.0.0.1:$Port"

$Captures = @(
    @{ Name = "01-command-center.png"; W = 1600; H = 1000; Query = "" },
    @{ Name = "02-office-overview.png"; W = 1920; H = 1080; Query = "" },
    @{ Name = "03-agent-inspector.png"; W = 1600; H = 1000; Query = "?inspect=ezzio_master" },
    @{ Name = "04-task-view.png"; W = 1440; H = 900; Query = "" },
    @{ Name = "05-hitl-view.png"; W = 1600; H = 1000; Query = "?modal=hitl" },
    @{ Name = "06-provider-view.png"; W = 1600; H = 600; Query = "" },
    @{ Name = "08-mobile-landscape.png"; W = 915; H = 412; Query = "" }
)

foreach ($c in $Captures) {
    $outPath = Join-Path $FullTargetDir $c.Name
    $targetUrl = if ($c.Query) { "$BaseUrl/$($c.Query)" } else { "$BaseUrl/" }
    Write-Host "[CAPTURE] $($c.Name) ($($c.W)x$($c.H)) -> $targetUrl..." -ForegroundColor Yellow
    & $BraveExe --headless=new "--screenshot=$outPath" "--window-size=$($c.W),$($c.H)" --virtual-time-budget=3500 --hide-scrollbars "$targetUrl"
    Start-Sleep -Milliseconds 800
}

# 2. Android device capture
if (Test-Path $AdbExe) {
    $dev = & $AdbExe devices | Select-String "device$"
    if ($dev) {
        $androidOut = Join-Path $FullTargetDir "07-mobile-portrait.png"
        Write-Host "[ANDROID] Capturing Android screen from emulator..." -ForegroundColor Magenta
        & $AdbExe exec-out screencap -p > $androidOut
        Write-Host "[OK] Android screenshot saved to $androidOut" -ForegroundColor Green
    } else {
        Write-Host "[SKIP] No Android emulator connected via ADB." -ForegroundColor Yellow
    }
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   VISUAL CAPTURE COMPLETED SUCCESSFULLY" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
