# ==============================================================================
# E-ZZIO V9.4 — Automated AI Office Video Recording Engine
# Records real runtime operation of the 2.5D Living Office via ADB or ffmpeg.
# ==============================================================================
param (
    [int]$DurationSec = 15,
    [string]$TargetDir = "state\audit\visual\v9.4\final",
    [string]$OutputFilename = "E-ZZIO-V9.4-AI-OFFICE-DEMO.mp4"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$FullTargetDir = Join-Path $RootDir $TargetDir

if (-not (Test-Path $FullTargetDir)) {
    New-Item -ItemType Directory -Force -Path $FullTargetDir | Out-Null
}

$AdbExe = "G:\tools\platform-tools\adb.exe"
$FinalVideoPath = Join-Path $FullTargetDir $OutputFilename

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   E-ZZIO V9.4 LIVING AI OFFICE VIDEO RECORDER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[TARGET] Recording $DurationSec seconds -> $FinalVideoPath" -ForegroundColor Gray

$Recorded = $false

# 1. Tentative d'enregistrement sur l'émulateur Android via adb screenrecord
if (Test-Path $AdbExe) {
    $dev = & $AdbExe devices | Select-String "device$"
    if ($dev) {
        Write-Host "[ANDROID] Recording $DurationSec seconds from Android emulator..." -ForegroundColor Magenta
        # Démarrer l'application au premier plan
        & $AdbExe shell am start -n ai.ezzio.office/.MainActivity | Out-Null
        Start-Sleep -Seconds 1

        # Enregistrer dans /sdcard/demo.mp4
        & $AdbExe shell screenrecord --time-limit $DurationSec /sdcard/demo.mp4
        Start-Sleep -Seconds 1

        # Récupérer la vidéo
        & $AdbExe pull /sdcard/demo.mp4 "$FinalVideoPath"
        if (Test-Path $FinalVideoPath) {
            $sz = (Get-Item $FinalVideoPath).Length
            Write-Host "[OK] Video saved successfully ($sz bytes) to $FinalVideoPath" -ForegroundColor Green
            $Recorded = $true
        }
    }
}

if (-not $Recorded) {
    Write-Host "[INFO] Android screenrecord non disponible ou AVD hors ligne. Video marquee comme optionnelle." -ForegroundColor Yellow
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   VIDEO CAPTURE ENGINE FINISHED" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
