param(
    [string]$Note = "réflexion confirmée : E-ZZIO doit rester prudent, propre, utile et sans action destructive automatique"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== E-ZZIO SAFE CONFIRM REFLECT ===" -ForegroundColor Cyan

$proposeBody = @{
    action = "human_reflect"
    params = @{
        note = $Note
    }
    reason = "réflexion human loop confirmée"
} | ConvertTo-Json -Depth 50

$proposal = Invoke-RestMethod "http://127.0.0.1:8000/safe-actions/propose" `
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

$run = Invoke-RestMethod "http://127.0.0.1:8000/safe-actions/run" `
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
    reflection = $run.result.reflection
    error = $run.error
}
