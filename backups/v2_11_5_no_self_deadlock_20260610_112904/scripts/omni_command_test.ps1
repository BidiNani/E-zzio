$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$BaseUrl = "http://127.0.0.1:8000"

Write-Host "=== E-ZZIO Omni Command Test ===" -ForegroundColor Cyan

$commands = @("/whoami", "/help", "/truth", "/everywhere", "/discord", "/messenger", "/mobile", "/noads")

foreach ($cmd in $commands) {
    Write-Host ""
    Write-Host ">>> $cmd" -ForegroundColor Yellow

    $body = @{
        text = $cmd
        source = "powershell"
        user = "enrik"
        mode = "fast"
    } | ConvertTo-Json -Depth 20

    $res = Invoke-RestMethod "$BaseUrl/omni-bridge/reply" `
        -Method POST `
        -ContentType "application/json" `
        -TimeoutSec 120 `
        -Body $body

    $res.reply
}
