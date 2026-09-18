$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO CLOUD BRAIN TEST ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1] Status" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\cloud_brain_status.ps1"

Write-Host ""
Write-Host "[2] Hybrid local-first" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\ezzio_hybrid_chat.ps1" -Text "E-ZZIO, fais un état rapide de ton système."

Write-Host ""
Write-Host "[3] Hybrid force cloud/fallback" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\ezzio_hybrid_chat.ps1" -Text "Cloud : résume en une phrase pourquoi E-ZZIO est local-first." -ForceCloud
