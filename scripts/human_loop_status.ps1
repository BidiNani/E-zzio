$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8001/human/status" -Method GET -TimeoutSec 90

Write-Host "=== E-ZZIO HUMAN STATUS ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    version = $res.version
    identity = $res.identity.name
    role = $res.identity.role
    style = $res.identity.style
    mode = $res.rhythm.mode
    last_tick = $res.rhythm.last_tick
    last_goal = $res.rhythm.last_goal
    health_ok = $res.health.ok
    maintenance_ok = $res.health.maintenance.ok
    brain_ok = $res.health.brain.ok
    gpu = $res.policy.gpu
    cpu_ram_only = $res.policy.cpu_ram_only
    no_ads = $res.policy.no_ads
    safe_only = $res.policy.safe_only
    journal = $res.journal_path
}

