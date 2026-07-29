param(
    [string]$Goal = "rester prêt, propre, rapide et utile sur PC",
    [string]$Context = "tick manuel demandé par Enrik",
    [switch]$PlanOnly
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
    goal = $Goal
    context = $Context
    execute = (-not [bool]$PlanOnly)
} | ConvertTo-Json -Depth 20

Invoke-RestMethod "http://127.0.0.1:8000/human/tick" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 180 `
    -Body $body
