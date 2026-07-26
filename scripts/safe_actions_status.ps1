$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8000/safe-actions/status" -Method GET -TimeoutSec 90

Write-Host "=== E-ZZIO SAFE ACTIONS STATUS ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    version = $res.version
    known_actions = $res.known_actions
    queued_count = $res.queued_count
    executed_count = $res.executed_count
    cancelled_count = $res.cancelled_count
    pending_count = $res.pending_count
    pending_confirmation = $res.pending_confirmation_count
    pending_read = $res.pending_read_count
    gpu = $res.policy.gpu
    no_ads = $res.policy.no_ads
    history = $res.policy.history
}
