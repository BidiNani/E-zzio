$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO HUMAN PC LOOP ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1] Human status" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\human_loop_status.ps1"

Write-Host ""
Write-Host "[2] Human tick" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\human_loop_tick.ps1" `
    -Goal "rester prêt, propre, rapide et utile sur PC" `
    -Context "routine human loop PC"

Write-Host ""
Write-Host "[3] Human reflection" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\human_loop_reflect.ps1"

Write-Host ""
Write-Host "[4] Journal récent" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\human_loop_journal.ps1" -Limit 8
