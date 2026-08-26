Set-Location "G:\AI\E-zzio"
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -notmatch "^#" -and $_ -match "=" } | ForEach-Object {
        $key, $value = $_.Split("=", 2)
        [System.Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim(), "Process")
    }
    Write-Host "[OK] Variables d'environnement (.env) chargées." -ForegroundColor Green
} else {
    Write-Host "[ERROR] Fichier .env manquant." -ForegroundColor Red
    exit 1
}

$PythonExe = ".\.venv\Scripts\python.exe"
Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "[*] Démarrage de l'API E-zzio sur le port 8001..." -ForegroundColor Cyan
& $PythonExe -m uvicorn interfaces.api.server:app --host 127.0.0.1 --port 8001