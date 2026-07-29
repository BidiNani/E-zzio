$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO ACTION CENTER v2.21.1 ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1] Registry" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_registry.ps1"

Write-Host ""
Write-Host "[2] Status" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_status.ps1"

Write-Host ""
Write-Host "[3] Queue" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_queue.ps1" -Limit 20

Write-Host ""
Write-Host "[4] Quick maintenance status" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_quick.ps1" -Action "maintenance_status"

Write-Host ""
Write-Host "[5] Quick brief" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_quick.ps1" -Action "human_chat_brief"

Write-Host ""
Write-Host "[6] Confirmed safe tick" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_confirm_tick.ps1" `
    -Goal "vérifier E-ZZIO sans rien casser" `
    -Context "action center v2.21.1"
