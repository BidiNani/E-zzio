param(
    [int]$Limit = 30
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8000/safe-actions/queue?limit=$Limit" -Method GET -TimeoutSec 90

Write-Host "=== E-ZZIO SAFE ACTIONS QUEUE ===" -ForegroundColor Cyan
Write-Host "Items : $($res.count)"
Write-Host ""

$res.items | ForEach-Object {
    [pscustomobject]@{
        created_at = $_.created_at
        status = $_.status
        id = $_.id
        action = $_.action
        requires_confirmation = $_.requires_confirmation
        safe = $_.safe
        destructive = $_.destructive
        reason = $_.reason
    }
}
