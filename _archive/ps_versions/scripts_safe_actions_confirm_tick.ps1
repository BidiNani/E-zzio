param(
    [string]$Goal = "surveiller E-ZZIO sans rien casser",
    [string]$Context = "validation manuelle Enrik via safe action queue"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO SAFE CONFIRM TICK ===" -ForegroundColor Cyan

$proposeBody = @{
    action = "human_tick_safe"
    params = @{
        goal = $Goal
        context = $Context
    }
    reason = "propose+run automatique avec confirmation explicite"
} | ConvertTo-Json -Depth 50

$proposal = Invoke-RestMethod "http://127.0.0.1:8001/safe-actions/propose" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 120 `
    -Body $proposeBody

if (-not $proposal.ok) {
    throw "Proposition échouée : $($proposal.error)"
}

Write-Host ""
Write-Host "Proposition créée :" -ForegroundColor Yellow
[pscustomobject]@{
    id = $proposal.id
    action = $proposal.action
    label = $proposal.label
    requires_confirmation = $proposal.requires_confirmation
    safe = $proposal.safe
    destructive = $proposal.destructive
}

$runBody = @{
    proposal_id = $proposal.id
    confirmation = "CONFIRME"
} | ConvertTo-Json -Depth 20

$run = Invoke-RestMethod "http://127.0.0.1:8001/safe-actions/run" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 180 `
    -Body $runBody

Write-Host ""
Write-Host "Exécution :" -ForegroundColor Yellow
[pscustomobject]@{
    ok = $run.ok
    proposal_id = $run.proposal_id
    action = $run.action
    elapsed_ms = $run.elapsed_ms
    result_ok = $run.result.ok
    summary = $run.result.summary
    error = $run.error
}

