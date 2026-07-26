$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$tests = @(
    @{
        text = "/help"
        session = "pc"
        task = "fast"
        speed = "fast"
        predict = 80
    },
    @{
        text = "/brief"
        session = "pc"
        task = "fast"
        speed = "fast"
        predict = 80
    },
    @{
        text = "E-ZZIO, prépare la prochaine optimisation PC sans rien casser."
        session = "pc"
        task = "companion"
        speed = "auto"
        predict = 220
    }
)

Write-Host "=== E-ZZIO HUMAN CHAT TEST ===" -ForegroundColor Cyan

foreach ($test in $tests) {
    Write-Host ""
    Write-Host ">>> $($test.text)" -ForegroundColor Yellow

    $body = $test | ConvertTo-Json -Depth 20

    $res = Invoke-RestMethod "http://127.0.0.1:8000/api/chat/human" `
        -Method POST `
        -ContentType "application/json" `
        -TimeoutSec 240 `
        -Body $body

    [pscustomobject]@{
        ok = $res.ok
        session = $res.session
        command = $res.command
        gateway = $res.gateway
        model = $res.route.model
        task = $res.route.task
        elapsed_ms = $(if ($null -ne $res.human_chat_elapsed_ms) { $res.human_chat_elapsed_ms } else { $res.elapsed_ms })
        deterministic = $res.deterministic
        reply = $res.reply
    }
}
