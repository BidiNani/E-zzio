$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO PC MAINTENANCE ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1] Status maintenance" -ForegroundColor Yellow
Invoke-RestMethod "http://127.0.0.1:8001/maintenance/status" -Method GET -TimeoutSec 60

Write-Host ""
Write-Host "[2] Audit PC" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\ezzio_audit_pc.ps1"

Write-Host ""
Write-Host "[3] Dust dry-run" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\ezzio_clean_dust.ps1"

