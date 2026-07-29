param(
    [string]$Note = "réflexion manuelle : garder E-ZZIO stable, humain, local-first et prudent"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
    note = $Note
} | ConvertTo-Json -Depth 10

Invoke-RestMethod "http://127.0.0.1:8000/human/reflect" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 90 `
    -Body $body
