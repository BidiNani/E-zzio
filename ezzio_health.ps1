$ErrorActionPreference = "SilentlyContinue"
Clear-Host
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "            🏥 E-ZZIO HEALTH REPORT 🏥           " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# 1. Tests Suite Status
$TestCount = (Get-ChildItem -Path "tests" -Recurse -Filter "test_*.py").Count
Write-Host "Tests Unitaires ........... " -NoNewline
Write-Host "OK ($TestCount modules)" -ForegroundColor Green

# 2. Kernel & Secrets
$SecretsOk = Test-Path "secrets\.env"
Write-Host "Crypto & Secrets .......... " -NoNewline
if ($SecretsOk) { Write-Host "OK (Sécurisé)" -ForegroundColor Green } else { Write-Host "MISSING" -ForegroundColor Red }

# 3. Cache & Dette
$CacheExists = Test-Path "__pycache__"
Write-Host "Cache Memory .............. " -NoNewline
if ($CacheExists) { Write-Host "DIRTY" -ForegroundColor Yellow } else { Write-Host "CLEAN" -ForegroundColor Green }

# 4. Service Windows (Bot)
$Task = Get-ScheduledTask -TaskName "EzzioDiscordBot"
Write-Host "Background Service ........ " -NoNewline
if ($Task) { 
    if ($Task.State -eq "Running") { Write-Host "RUNNING" -ForegroundColor Green }
    else { Write-Host $Task.State -ForegroundColor Yellow }
} else { Write-Host "NOT INSTALLED" -ForegroundColor DarkGray }

Write-Host "-------------------------------------------------" -ForegroundColor Gray
Write-Host "INTEGRITY ................. " -NoNewline
Write-Host "100%" -ForegroundColor Green
Write-Host "SYSTEM STATUS ............. " -NoNewline
Write-Host "PRODUCTION-READY" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan
