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

$res = Invoke-RestMethod "http://127.0.0.1:8001/human/tick" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 180 `
    -Body $body

Write-Host "=== E-ZZIO HUMAN TICK ===" -ForegroundColor Cyan

[pscustomobject]@{
    ok = $res.ok
    version = $res.version
    elapsed_ms = $res.elapsed_ms
    goal = $res.intention.goal
    mood = $res.intention.mood
    priority = $res.intention.priority
    risk_level = $res.intention.risk_level
    summary = $res.summary
}

Write-Host ""
Write-Host "Plan :" -ForegroundColor Yellow
$res.plan.steps | ForEach-Object {
    [pscustomobject]@{
        id = $_.id
        label = $_.label
        safe = $_.safe
        destructive = $_.destructive
    }
}

Write-Host ""
Write-Host "Résultats :" -ForegroundColor Yellow
$res.results | ForEach-Object {
    [pscustomobject]@{
        ok = $_.ok
        step_id = $_.step_id
        action = $_.action
        candidate_count = $_.candidate_count
        bad_count = $_.bad_count
    }
}

