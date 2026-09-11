# ==============================================================================
# E-ZZIO V9.0 — Canonical Desktop Software Launcher (Windows)
# Démarre le serveur souverain et ouvre la fenêtre applicative locale.
# ==============================================================================
param (
    [switch]$Headless,
    [string]$Port = "8001",
    [switch]$AppMode
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "[FATAL] Python venv introuvable : $PythonExe"
    exit 1
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   E-ZZIO SOVEREIGN DESKTOP APPLICATION (V9.0.0)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "[INIT] Vérification du serveur souverain sur le port $Port..." -ForegroundColor Gray

# Démarrage ou vérification du serveur web
$ServerUrl = "http://127.0.0.1:$Port"
$Running = $false

try {
    $res = Invoke-RestMethod -Uri "$ServerUrl/health" -TimeoutSec 1 -ErrorAction SilentlyContinue
    if ($res.status -eq "ONLINE") {
        $Running = $true
        Write-Host "[OK] Serveur E-ZZIO déjà actif (PID: $($res.pid))." -ForegroundColor Green
    }
} catch {}

if (-not $Running) {
    Write-Host "[START] Démarrage du WebServer en arrière-plan..." -ForegroundColor Yellow
    $Proc = Start-Process -FilePath $PythonExe -ArgumentList "-m", "uvicorn", "web_server:app", "--host", "127.0.0.1", "--port", $Port -WorkingDirectory $RootDir -PassThru
    Start-Sleep -Seconds 2
    Write-Host "[OK] Serveur démarré avec succès (PID: $($Proc.Id))." -ForegroundColor Green
}

if (-not $Headless) {
    Write-Host "[LAUNCH] Ouverture de l'espace de travail Desktop E-ZZIO AI Office..." -ForegroundColor Cyan
    # Détection dynamique du moteur Chromium pour affichage fenêtré autonome 1600x1000 (--app)
    $ChromiumCandidates = @(
        "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        "C:\Program Files\Google\Chrome\Application\chrome.exe",
        "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    )
    $AppLauncher = $null
    foreach ($candidate in $ChromiumCandidates) {
        if (Test-Path $candidate) {
            $AppLauncher = $candidate
            break
        }
    }
    if ($AppLauncher) {
        Write-Host "[LAUNCH] Mode application standalone via : $AppLauncher" -ForegroundColor DarkCyan
        Start-Process $AppLauncher -ArgumentList "--app=$ServerUrl", "--window-size=1600,1000"
    } else {
        Start-Process $ServerUrl
    }
}

Write-Host "[SUCCESS] E-ZZIO Desktop prêt : $ServerUrl" -ForegroundColor Green
