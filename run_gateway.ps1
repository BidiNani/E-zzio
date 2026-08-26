# Script de démarrage de la passerelle E-zzio
Set-Location "G:\AI\E-zzio"

# Chargement du .env local
if (Test-Path "G:\AI\E-zzio\config\.env") {
    Get-Content "G:\AI\E-zzio\config\.env" | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $val = $matches[2].Trim().Trim('"')
            [System.Environment]::SetEnvironmentVariable($name, $val, 'Process')
        }
    }
}

Write-Host "Lancement de LiteLLM Proxy sur http://127.0.0.1:4000..." -ForegroundColor Cyan
& .\.venv\Scripts\litellm.exe --config "G:\AI\E-zzio\config\litellm_config.yaml" --port 4000 --host 127.0.0.1
