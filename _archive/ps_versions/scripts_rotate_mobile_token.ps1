param(
    [int]$Bytes = 32
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$SecretsRoot = Join-Path $ProjectRoot "secrets"
$EnvPath = Join-Path $SecretsRoot "omnipresence.env"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupRoot = Join-Path $ProjectRoot "backups\rotate_mobile_token_$Stamp"

New-Item -ItemType Directory -Force -Path $SecretsRoot, $BackupRoot | Out-Null

if (Test-Path -LiteralPath $EnvPath) {
    Copy-Item -LiteralPath $EnvPath -Destination (Join-Path $BackupRoot "omnipresence.env.before_rotate") -Force
}

$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$bytesBuffer = New-Object byte[] $Bytes
$rng.GetBytes($bytesBuffer)
$token = [Convert]::ToBase64String($bytesBuffer).TrimEnd("=").Replace("+", "-").Replace("/", "_")

$lines = @()
if (Test-Path -LiteralPath $EnvPath) {
    $lines = Get-Content -LiteralPath $EnvPath -Encoding UTF8
}

$found = $false
$newLines = foreach ($line in $lines) {
    if ($line -match "^EZZIO_MOBILE_TOKEN=") {
        $found = $true
        "EZZIO_MOBILE_TOKEN=$token"
    }
    else {
        $line
    }
}

if (-not $found) {
    $newLines += "EZZIO_MOBILE_TOKEN=$token"
}

$newLines | Set-Content -LiteralPath $EnvPath -Encoding UTF8

[pscustomobject]@{
    ok = $true
    env_path = $EnvPath
    backup = $BackupRoot
    token_length = $token.Length
    message = "Token mobile renouvelé. Redémarre l'API pour prise en compte si nécessaire."
}
