#requires -Version 5.1
$ErrorActionPreference = "SilentlyContinue"
$ProjectRoot = "G:\AI\E-zzio"
$PythonExe   = "G:\Python312\python.exe"

Write-Host "=== LANCEMENT D'E-ZZIO (100% Local & Unifié) ===" -ForegroundColor Cyan

$tcp = Get-NetTCPConnection -LocalPort 8000 -State Listen
if ($tcp) { Stop-Process -Id $tcp.OwningProcess -Force }
Start-Sleep -Seconds 1

Write-Host "🚀 Lancement du Cerveau FastAPI..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'E-zzio - FastAPI Local'; Set-Location -LiteralPath '$ProjectRoot'; & '$PythonExe' web_server.py" -WindowStyle Normal
Start-Sleep -Seconds 3

Write-Host "🚀 Lancement du Bot Discord..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'E-zzio - Discord Bot Local'; Set-Location -LiteralPath '$ProjectRoot'; & '$PythonExe' discord_agent.py" -WindowStyle Normal

Write-Host "✅ TOUT EST PRÊT ET LANCÉ !" -ForegroundColor Green