param(
    [ValidateSet("fast", "normal", "deep")]
    [string]$Level = "fast"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{ level = $Level } | ConvertTo-Json -Depth 10

Invoke-RestMethod "http://127.0.0.1:8001/performance/warmup" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 600 `
    -Body $body

