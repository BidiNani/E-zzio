$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8000/human-chat/brief" -Method GET -TimeoutSec 120

Write-Host "=== E-ZZIO HUMAN CHAT BRIEF ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    version = $res.version
    summary = $res.summary
    maintenance_ok = $res.maintenance.ok
    bad_count = $res.maintenance.bad_count
    dust = $res.maintenance.dust_candidate_count
    brain_version = $res.brain.version
    installed_models = $res.brain.installed_count
    last_tick = $res.human.rhythm.last_tick
}
