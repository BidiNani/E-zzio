param(
    [switch]$AllowSend,
    [string]$Provider = "",
    [string]$ApiKey = "",
    [string]$Model = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$envPath = "G:\AI\E-zzio\secrets\cloud_brain.env"

if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item "G:\AI\E-zzio\secrets\cloud_brain.env.example" $envPath -Force
}

$content = Get-Content -LiteralPath $envPath -Raw -Encoding UTF8

function Set-EnvLine {
    param(
        [string]$Content,
        [string]$Key,
        [string]$Value
    )

    $escapedKey = [regex]::Escape($Key)
    if ($Content -match "(?m)^$escapedKey=") {
        return [regex]::Replace($Content, "(?m)^$escapedKey=.*$", "$Key=$Value")
    }

    return $Content.TrimEnd() + [Environment]::NewLine + "$Key=$Value" + [Environment]::NewLine
}

if ($AllowSend) {
    $content = Set-EnvLine -Content $content -Key "EZZIO_CLOUD_ALLOW_SEND" -Value "true"
}

if ($Provider -and $ApiKey) {
    switch ($Provider.ToLowerInvariant()) {
        "gemini" {
            $content = Set-EnvLine -Content $content -Key "GEMINI_API_KEY" -Value $ApiKey
            if ($Model) { $content = Set-EnvLine -Content $content -Key "GEMINI_MODEL" -Value $Model }
        }
        "groq" {
            $content = Set-EnvLine -Content $content -Key "GROQ_API_KEY" -Value $ApiKey
            if ($Model) { $content = Set-EnvLine -Content $content -Key "GROQ_MODEL" -Value $Model }
        }
        "openrouter" {
            $content = Set-EnvLine -Content $content -Key "OPENROUTER_API_KEY" -Value $ApiKey
            if ($Model) { $content = Set-EnvLine -Content $content -Key "OPENROUTER_MODEL" -Value $Model }
        }
        default {
            throw "Provider inconnu. Utilise gemini, groq ou openrouter."
        }
    }
}

Set-Content -LiteralPath $envPath -Value $content -Encoding UTF8

try {
    icacls $envPath /inheritance:r | Out-Null
    icacls $envPath /grant:r "$env:USERNAME:(R,W)" | Out-Null
}
catch {}

Write-Host "=== E-ZZIO CLOUD BRAIN CONFIG UPDATED ===" -ForegroundColor Cyan
[pscustomobject]@{
    env_path = $envPath
    allow_send_requested = [bool]$AllowSend
    provider_updated = $Provider
    model_updated = $Model
    note = "Redémarre l'API E-ZZIO après modification des clés."
}
