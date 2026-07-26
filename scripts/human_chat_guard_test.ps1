$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$tests = @(
    @{
        text = "E-ZZIO, fais un état rapide de ton système."
        session = "pc"
        task = "auto"
        speed = "fast"
        predict = 100
    },
    @{
        text = "E-ZZIO, prépare la prochaine optimisation PC sans rien casser."
        session = "pc"
        task = "auto"
        speed = "auto"
        predict = 160
    },
    @{
        text = "/brief"
        session = "pc"
        task = "fast"
        speed = "fast"
        predict = 80
    }
)

Write-Host "=== E-ZZIO HUMAN CHAT TRUTH GUARD TEST ===" -ForegroundColor Cyan

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
        truth_guard = $res.truth_guard
        deterministic = $res.deterministic
        model = $res.route.model
        task = $res.route.task
        elapsed_ms = $(if ($null -ne $res.human_chat_elapsed_ms) { $res.human_chat_elapsed_ms } else { $res.elapsed_ms })
        reply = $res.reply
    }
}
