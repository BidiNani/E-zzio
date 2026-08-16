param(
    [string]$Reason = "nettoyage des anciennes propositions pending"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
    reason = $Reason
} | ConvertTo-Json -Depth 20

$res = Invoke-RestMethod "http://127.0.0.1:8001/safe-actions/cancel-pending" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 180 `
    -Body $body

Write-Host "=== E-ZZIO SAFE ACTION CANCEL PENDING ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    pending_before = $res.pending_before
    cancelled_count = $res.cancelled_count
    errors_count = $res.errors_count
}

