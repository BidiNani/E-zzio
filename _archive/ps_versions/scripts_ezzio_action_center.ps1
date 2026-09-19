$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO ACTION CENTER v2.22 ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1] Commander status" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\commander_status.ps1"

Write-Host ""
Write-Host "[2] Safe actions status" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_status.ps1"

Write-Host ""
Write-Host "[3] Commander quick state" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\ezzio_commander_pc.ps1" -Text "E-ZZIO, fais un état rapide de ton système."

Write-Host ""
Write-Host "[4] Commander proposal" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\ezzio_commander_pc.ps1" -Text "E-ZZIO, prépare la prochaine optimisation PC sans rien casser."

Write-Host ""
Write-Host "[5] Commander confirm" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\ezzio_commander_pc.ps1" -Text "CONFIRME"

Write-Host ""
Write-Host "[6] Ledger" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_ledger.ps1" -Limit 20
