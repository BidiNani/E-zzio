param(
    [Parameter(Mandatory=$true)]
    [string]$ProposalId,

    [string]$Confirmation = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
    proposal_id = $ProposalId
    confirmation = $Confirmation
} | ConvertTo-Json -Depth 20

$res = Invoke-RestMethod "http://127.0.0.1:8000/safe-actions/run" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 180 `
    -Body $body

Write-Host "=== E-ZZIO SAFE ACTION RUN ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    action = $res.action
    proposal_id = $res.proposal_id
    elapsed_ms = $res.elapsed_ms
    error = $res.error
    result_ok = $res.result.ok
}
