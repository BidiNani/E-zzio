$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8001/commander/status" -Method GET -TimeoutSec 90

Write-Host "=== E-ZZIO PC COMMANDER STATUS ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    version = $res.version
    commander_root = $res.commander_root
    journal_path = $res.journal_path
    session_count = $res.sessions.Count
    commands = ($res.commands -join ", ")
    gpu = $res.policy.gpu
    no_ads = $res.policy.no_ads
    confirmation_word = $res.policy.confirmation_word
}

