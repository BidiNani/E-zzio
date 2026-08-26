Set-Location "G:\AI\E-zzio"
$PythonExe = ".\.venv\Scripts\python.exe"
$LogDir = "runtime\logs"
New-Item -ItemType Directory -Force $LogDir | Out-Null

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "   E-ZZIO — SUPERVISEUR DE PROCESSUS LOCAL           " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# Chargement .env
if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -notmatch "^#" -and $_ -match "=" } | ForEach-Object {
        $k, $v = $_.Split("=", 2)
        [System.Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), "Process")
    }
}

Write-Host "[INFO] Démarrage de la boucle de surveillance (CTRL+C pour stopper)..." -ForegroundColor Green

try {
    while ($true) {
        $proc = Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -like "*uvicorn*" }
        if (-not $proc) {
            Write-Host "[WARN] Processus arrêté. Redémarrage..." -ForegroundColor Yellow
            Start-Process -NoNewWindow -FilePath $PythonExe -ArgumentList "-m", "uvicorn", "interfaces.api.server:app", "--host", "127.0.0.1", "--port", "8001"
            Start-Sleep -Seconds 3
        }
        Start-Sleep -Seconds 5
    }
} finally {
    Write-Host "`n[INFO] Arrêt du superviseur..." -ForegroundColor Yellow
    Get-Process | Where-Object { $_.ProcessName -eq "python" -and $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Processus nettoyés." -ForegroundColor Green
}