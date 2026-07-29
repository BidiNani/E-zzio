$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO ACTION CENTER v2.21.3 ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1] Status" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_status.ps1"

Write-Host ""
Write-Host "[2] Ledger" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_ledger.ps1" -Limit 20

Write-Host ""
Write-Host "[3] Quick maintenance status" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_quick.ps1" -Action "maintenance_status"

Write-Host ""
Write-Host "[4] Confirmed safe tick" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_confirm_tick.ps1" `
    -Goal "vérifier E-ZZIO sans rien casser" `
    -Context "action center v2.21.3"

Write-Host ""
Write-Host "[5] Status final" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_status.ps1"
