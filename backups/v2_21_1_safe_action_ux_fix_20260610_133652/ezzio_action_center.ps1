$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO ACTION CENTER ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1] Registry" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_registry.ps1"

Write-Host ""
Write-Host "[2] Status" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_status.ps1"

Write-Host ""
Write-Host "[3] Quick maintenance status" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_quick.ps1" -Action "maintenance_status"

Write-Host ""
Write-Host "[4] Quick brief" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_quick.ps1" -Action "human_chat_brief"

Write-Host ""
Write-Host "[5] Proposed safe tick requiring confirmation" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\safe_actions_propose.ps1" `
    -Action "human_tick_safe" `
    -ParamsJson '{"goal":"vérifier E-ZZIO sans rien casser","context":"action center v2.21"}' `
    -Reason "test proposition contrôlée"
