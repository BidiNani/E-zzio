param(
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{ apply = [bool]$Apply } | ConvertTo-Json -Depth 10

Invoke-RestMethod "http://127.0.0.1:8001/maintenance/dust" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 180 `
    -Body $body

