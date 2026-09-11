$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8001/human-chat/status" -Method GET -TimeoutSec 90

Write-Host "=== E-ZZIO HUMAN CHAT STATUS ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    version = $res.version
    chat_root = $res.chat_root
    sessions_root = $res.sessions_root
    cpu_ram_only = $res.policy.cpu_ram_only
    gpu = $res.policy.gpu
    no_ads = $res.policy.no_ads
    safe_only = $res.policy.safe_only
    commands = ($res.commands -join ", ")
}

