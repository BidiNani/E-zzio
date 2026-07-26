$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$envPath = "G:\AI\E-zzio\secrets\cloud_brain.env"

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "cloud_brain.env introuvable."
}

$content = Get-Content -LiteralPath $envPath -Raw -Encoding UTF8

if ($content -match "(?m)^EZZIO_CLOUD_ALLOW_SEND=") {
    $content = [regex]::Replace($content, "(?m)^EZZIO_CLOUD_ALLOW_SEND=.*$", "EZZIO_CLOUD_ALLOW_SEND=false")
}
else {
    $content += [Environment]::NewLine + "EZZIO_CLOUD_ALLOW_SEND=false" + [Environment]::NewLine
}

Set-Content -LiteralPath $envPath -Value $content -Encoding UTF8

Write-Host "=== E-ZZIO CLOUD BRAIN DISABLED ===" -ForegroundColor Cyan
[pscustomobject]@{
    env_path = $envPath
    allow_send = $false
    note = "Redémarre l'API E-ZZIO pour appliquer."
}
