Set-Location "G:\AI\E-zzio"
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "   E-ZZIO — DÉMARRAGE CONTENEUR DOCKER               " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

try {
    docker --version | Out-Null
    Write-Host "[OK] Démon Docker opérationnel." -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker non détecté dans le PATH système." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host "[ERROR] Fichier .env manquant." -ForegroundColor Red
    exit 1
}

Write-Host "[*] Démarrage du conteneur ezzio-api..." -ForegroundColor Cyan
docker compose up -d --build
Write-Host "[OK] Conteneur en exécution sur http://localhost:8001" -ForegroundColor Green