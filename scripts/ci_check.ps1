# Script PowerShell CI/CD local pour E-ZzIO
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         E-ZZIO LOCAL CI/CD VALIDATION RUNNER          " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $RootDir

# 1. Exécution du pré-commit Python
& "G:\Python312\python.exe" "scripts/pre_commit.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Le pipeline CI/CD a échoué." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "✔ Pipeline CI/CD terminé avec succès." -ForegroundColor Green
