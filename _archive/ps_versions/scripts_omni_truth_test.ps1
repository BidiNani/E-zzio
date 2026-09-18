$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$BaseUrl = "http://127.0.0.1:8001"

Write-Host "=== E-ZZIO Truth Guard Test v2.11.5 ===" -ForegroundColor Cyan

$tests = @(
    "Peux-tu être sur mon smartphone ?",
    "Est-ce que Discord est actif ?",
    "Est-ce que Messenger est actif ?",
    "Est-ce que tu as des commandes vocales ?",
    "Le bridge E-ZZIO est-il réparé ?",
    "/noads",
    "/truth"
)

foreach ($text in $tests) {
    Write-Host ""
    Write-Host ">>> $text" -ForegroundColor Yellow

    $body = @{
        text = $text
        source = "mobile"
        user = "enrik"
        mode = "fast"
    } | ConvertTo-Json -Depth 20

    $res = Invoke-RestMethod "$BaseUrl/omni-bridge/reply" `
        -Method POST `
        -ContentType "application/json" `
        -TimeoutSec 90 `
        -Body $body

    $res.reply
}

