$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$BaseUrl = "http://127.0.0.1:8000"

$tests = @(
    "Le bridge E-ZZIO est-il réparé ?",
    "Peux-tu être sur mon smartphone ?",
    "Explique ton rôle partout, sans pub.",
    "Donne-moi les commandes utiles."
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
        -TimeoutSec 180 `
        -Body $body

    $res.reply
}
