$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$BaseUrl = "http://127.0.0.1:8000"

Write-Host "=== E-ZZIO Omni Command Test v2.11.5 ===" -ForegroundColor Cyan

$commands = @("/status", "/routers", "/noads", "/forge", "/vision", "/truth", "/everywhere", "/help")

foreach ($cmd in $commands) {
    Write-Host ""
    Write-Host ">>> $cmd" -ForegroundColor Yellow

    $body = @{
        text = $cmd
        source = "powershell"
        user = "enrik"
        mode = "fast"
    } | ConvertTo-Json -Depth 20

    $started = Get-Date

    $res = Invoke-RestMethod "$BaseUrl/omni-bridge/reply" `
        -Method POST `
        -ContentType "application/json" `
        -TimeoutSec 60 `
        -Body $body

    $elapsed = [math]::Round(((Get-Date) - $started).TotalMilliseconds, 0)
    Write-Host "Elapsed: $elapsed ms" -ForegroundColor DarkGray
    $res.reply
}
