$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO CLOUD BRAIN TEST ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1] Status" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\cloud_brain_status.ps1"

Write-Host ""
Write-Host "[2] Route local/cloud" -ForegroundColor Yellow

$body = @{
    text = "Analyse complexe via API cloud si disponible, sinon local."
    provider = "auto"
} | ConvertTo-Json -Depth 20

$route = Invoke-RestMethod "http://127.0.0.1:8000/cloud-brain/route" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 90 `
    -Body $body

[pscustomobject]@{
    ok = $route.ok
    decision = $route.decision
    allow_send = $route.allow_send
    reasons = ($route.reasons -join ", ")
}

Write-Host ""
Write-Host "[3] Hybrid local-first" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\ezzio_hybrid_chat.ps1" -Text "E-ZZIO, fais un état rapide de ton système."

Write-Host ""
Write-Host "[4] Hybrid force cloud, fallback si désactivé" -ForegroundColor Yellow
& "G:\AI\E-zzio\scripts\ezzio_hybrid_chat.ps1" -Text "Cloud : résume en une phrase pourquoi E-ZZIO est local-first." -ForceCloud
