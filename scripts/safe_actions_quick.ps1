param(
    [Parameter(Mandatory=$true)]
    [string]$Action,

    [string]$ParamsJson = "{}"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

try {
    $paramsObject = $ParamsJson | ConvertFrom-Json
}
catch {
    throw "ParamsJson invalide. Exemple : '{""goal"":""tester""}'"
}

$body = @{
    action = $Action
    params = $paramsObject
} | ConvertTo-Json -Depth 50

$res = Invoke-RestMethod "http://127.0.0.1:8000/safe-actions/quick" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 180 `
    -Body $body

Write-Host "=== E-ZZIO SAFE ACTION QUICK ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    queued = $res.queued
    requires_confirmation = $res.requires_confirmation
    action = $res.action
    proposal_id = $res.proposal_id
    elapsed_ms = $res.elapsed_ms
    message = $res.message
    result_ok = $res.result.ok
}
