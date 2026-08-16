param(
    [Parameter(Mandatory=$true)]
    [string]$Action,

    [string]$ParamsJson = "{}",

    [string]$Reason = "proposition manuelle Enrik"
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
    reason = $Reason
} | ConvertTo-Json -Depth 50

$res = Invoke-RestMethod "http://127.0.0.1:8001/safe-actions/propose" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 120 `
    -Body $body

Write-Host "=== E-ZZIO SAFE ACTION PROPOSE ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    id = $res.id
    action = $res.action
    label = $res.label
    requires_confirmation = $res.requires_confirmation
    safe = $res.safe
    destructive = $res.destructive
    reason = $res.reason
}

