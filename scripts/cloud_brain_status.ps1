$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8001/cloud-brain/status" -Method GET -TimeoutSec 90

Write-Host "=== E-ZZIO CLOUD BRAIN STATUS ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    version = $res.version
    allow_send = $res.allow_send
    mode = $res.mode
    total_today = $res.usage.total_today
    daily_total_limit = $res.daily_total_limit
    cache_count = $res.cache_count
    secrets_path = $res.secrets_path
    gpu = $res.policy.gpu
    no_ads = $res.policy.no_ads
}

Write-Host ""
Write-Host "Providers :" -ForegroundColor Yellow
$res.providers | ForEach-Object {
    [pscustomobject]@{
        provider = $_.provider
        configured = $_.configured
        model = $_.model
        today_used = $_.today_used
        daily_limit = $_.daily_limit
        remaining = $_.remaining
        usable = $_.usable
    }
}

