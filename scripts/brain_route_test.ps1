$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$tests = @(
    @{ text = "Qui es-tu E-ZZIO ?"; task = "auto"; speed = "auto" },
    @{ text = "Fais un script PowerShell propre avec logs et backup."; task = "auto"; speed = "auto" },
    @{ text = "Réponds très vite : statut rapide."; task = "auto"; speed = "fast" },
    @{ text = "Analyse profondément l'architecture du projet."; task = "deep"; speed = "deep" },
    @{ text = "Analyse une image ou capture."; task = "vision"; speed = "auto" }
)

foreach ($test in $tests) {
    Write-Host ""
    Write-Host ">>> $($test.text)" -ForegroundColor Yellow

    $body = $test | ConvertTo-Json -Depth 10

    Invoke-RestMethod "http://127.0.0.1:8001/brain/route" `
        -Method POST `
        -ContentType "application/json" `
        -TimeoutSec 60 `
        -Body $body
}

