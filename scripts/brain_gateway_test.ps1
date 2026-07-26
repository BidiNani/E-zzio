$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$tests = @(
    @{
        endpoint = "http://127.0.0.1:8000/api/brain/chat"
        body = @{
            text = "Qui es-tu E-ZZIO ? Réponds en une phrase."
            task = "identity"
            speed = "auto"
            predict = 120
        }
    },
    @{
        endpoint = "http://127.0.0.1:8000/api/chat/pc"
        body = @{
            text = "Donne-moi une règle PowerShell E-ZZIO courte et concrète."
            task = "powershell"
            speed = "auto"
            predict = 180
        }
    },
    @{
        endpoint = "http://127.0.0.1:8000/api/chat/router"
        body = @{
            text = "Réponds vite : E-ZZIO est-il CPU/RAM only ?"
            task = "fast"
            speed = "fast"
            predict = 80
        }
    }
)

foreach ($test in $tests) {
    Write-Host ""
    Write-Host ">>> $($test.endpoint)" -ForegroundColor Yellow

    $json = $test.body | ConvertTo-Json -Depth 10

    $res = Invoke-RestMethod $test.endpoint `
        -Method POST `
        -ContentType "application/json" `
        -TimeoutSec 240 `
        -Body $json

    [pscustomobject]@{
        ok = $res.ok
        gateway = $res.gateway
        task = $res.route.task
        model = $res.route.model
        elapsed_ms = $res.elapsed_ms
        reply = $res.reply
    }
}
