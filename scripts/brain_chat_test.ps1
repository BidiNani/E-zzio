$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$tests = @(
    @{
        text = "Qui es-tu E-ZZIO ? Réponds en une phrase."
        task = "identity"
        speed = "auto"
        predict = 120
    },
    @{
        text = "Donne-moi une règle courte pour écrire des scripts PowerShell E-ZZIO propres."
        task = "powershell"
        speed = "auto"
        predict = 160
    },
    @{
        text = "Réponds vite : E-ZZIO est-il CPU/RAM only ?"
        task = "fast"
        speed = "fast"
        predict = 80
    }
)

foreach ($test in $tests) {
    Write-Host ""
    Write-Host ">>> $($test.task) / $($test.speed)" -ForegroundColor Yellow

    $body = $test | ConvertTo-Json -Depth 10

    $res = Invoke-RestMethod "http://127.0.0.1:8000/brain/chat" `
        -Method POST `
        -ContentType "application/json" `
        -TimeoutSec 240 `
        -Body $body

    [pscustomobject]@{
        ok = $res.ok
        task = $res.route.task
        model = $res.route.model
        elapsed_ms = $res.elapsed_ms
        reply = $res.reply
    }
}
