# =============================================================================
# E-ZZIO — DÉMARRAGE SÉCURISÉ
# =============================================================================

Set-Location "G:\AI\E-zzio"

# Charger les variables d'environnement
if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -notmatch "^#" -and $_ -match "=" } | ForEach-Object {
        $key, $value = # =============================================================================
# E-ZZIO — DÉMARRAGE SÉCURISÉ
# =============================================================================

Set-Location "G:\AI\E-zzio"

# Charger les variables d'environnement
if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -notmatch "^#" -and $_ -match "=" } | ForEach-Object {
        $key, $value = $_.Split("=", 2)
        [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        Write-Host "[OK] $key chargé." -ForegroundColor Green
    }
} else {
    Write-Host "[ERROR] .env introuvable ! Créez-le avec EZZIO_API_KEY." -ForegroundColor Red
    exit 1
}

# Vérifier que la clé API est définie
$ApiKey = [System.Environment]::GetEnvironmentVariable("EZZIO_API_KEY", "Process")
if (-not $ApiKey) {
    Write-Host "[ERROR] EZZIO_API_KEY non définie !" -ForegroundColor Red
    exit 1
}

Write-Host "
[OK] Démarrage d'E-zzio..." -ForegroundColor Green

# Démarrer l'API
$PythonExe = ".\.venv\Scripts\python.exe"
& $PythonExe -m uvicorn interfaces.api.server:app --host 127.0.0.1 --port 8001.Split("=", 2)
        [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        Write-Host "[OK] $key chargé." -ForegroundColor Green
    }
} else {
    Write-Host "[ERROR] .env introuvable ! Créez-le avec EZZIO_API_KEY." -ForegroundColor Red
    exit 1
}

# Vérifier que la clé API est définie
$ApiKey = [System.Environment]::GetEnvironmentVariable("EZZIO_API_KEY", "Process")
if (-not $ApiKey) {
    Write-Host "[ERROR] EZZIO_API_KEY non définie !" -ForegroundColor Red
    exit 1
}

Write-Host "
[OK] Démarrage d'E-zzio..." -ForegroundColor Green

# Démarrer l'API
$PythonExe = ".\.venv\Scripts\python.exe"
& $PythonExe -m uvicorn interfaces.api.server:app --host 127.0.0.1 --port 8001