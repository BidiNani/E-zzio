$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ============================================================
# E-ZZIO - Rotate mobile token
# ============================================================

$ProjectRoot = "G:\AI\E-zzio"
$EnvPath = Join-Path $ProjectRoot "secrets\omnipresence.env"

if (-not (Test-Path -LiteralPath $EnvPath)) {
    throw "Fichier secrets introuvable : $EnvPath"
}

$newToken = [Guid]::NewGuid().ToString("N") + [Guid]::NewGuid().ToString("N").Substring(0, 16)
$text = Get-Content -LiteralPath $EnvPath -Raw -Encoding UTF8

if ($text -match "EZZIO_MOBILE_SHARED_TOKEN=") {
    $text = $text -replace "EZZIO_MOBILE_SHARED_TOKEN=.*", "EZZIO_MOBILE_SHARED_TOKEN=$newToken"
}
else {
    $text = $text.TrimEnd() + "`r`nEZZIO_MOBILE_SHARED_TOKEN=$newToken`r`n"
}

Set-Content -LiteralPath $EnvPath -Value $text -Encoding UTF8

Write-Host "✅ Nouveau token mobile :" -ForegroundColor Green
Write-Host $newToken
Write-Host ""
Write-Host "Redémarre l'API pour prise en compte."
