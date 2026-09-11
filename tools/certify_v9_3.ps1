# ==============================================================================
# E-ZZIO V9.3 — Master Forensic Certification Script (PowerShell Wrapper)
# ==============================================================================
param (
    [switch]$SkipTests = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Set-Location $RootDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   E-ZZIO V9.3 VISUAL REVEAL & PRODUCT UX CERTIFIER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

& $PythonExe (Join-Path $RootDir "tools\certify_v9_3.py")
if ($LASTEXITCODE -ne 0) {
    Write-Error "[FAIL] Certification V9.3 a echoue !"
    exit 1
}

Write-Host "============================================================" -ForegroundColor Green
Write-Host "   V9.3 CERTIFICATION TERMINEE AVEC SUCCES !" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
