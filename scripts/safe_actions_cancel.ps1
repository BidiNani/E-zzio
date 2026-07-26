param(
    [Parameter(Mandatory=$true)]
    [string]$ProposalId,

    [string]$Reason = "annulation manuelle Enrik"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
    proposal_id = $ProposalId
    reason = $Reason
} | ConvertTo-Json -Depth 20

$res = Invoke-RestMethod "http://127.0.0.1:8000/safe-actions/cancel" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 120 `
    -Body $body

Write-Host "=== E-ZZIO SAFE ACTION CANCEL ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    proposal_id = $res.proposal_id
    action = $res.action
    already_cancelled = $res.already_cancelled
    reason = $res.reason
    error = $res.error
    message = $res.message
}
