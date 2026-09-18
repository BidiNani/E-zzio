$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$BaseUrl = "http://127.0.0.1:8001"

$result = Invoke-RestMethod "$BaseUrl/forge/image/upscale-latest-1080p" `
    -Method POST `
    -TimeoutSec 120

$result

if ($result.ok) {
    Write-Host ""
    Write-Host "✅ Image HD créée : $($result.output)" -ForegroundColor Green
}
else {
    Write-Warning $result.error
}

