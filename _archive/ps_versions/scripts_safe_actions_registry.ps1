$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8001/safe-actions/registry" -Method GET -TimeoutSec 90

Write-Host "=== E-ZZIO SAFE ACTIONS REGISTRY ===" -ForegroundColor Cyan

$res.actions.PSObject.Properties | ForEach-Object {
    $name = $_.Name
    $spec = $_.Value
    [pscustomobject]@{
        action = $name
        label = $spec.label
        safe = $spec.safe
        destructive = $spec.destructive
        requires_confirmation = $spec.requires_confirmation
        kind = $spec.kind
    }
}

