$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8000/safe-actions/status" -Method GET -TimeoutSec 90

Write-Host "=== E-ZZIO SAFE ACTIONS STATUS ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    version = $res.version
    known_actions = $res.known_actions
    queued_count = $res.queued_count
    pending_count = $res.pending_count
    queue_path = $res.queue_path
    runs_path = $res.runs_path
    gpu = $res.policy.gpu
    no_ads = $res.policy.no_ads
    confirmation_word = $res.policy.confirmation_word
}
