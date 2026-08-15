# ==============================================================================
# E-ZZIO — Sovereign API Runtime Launcher (v2.3 - Production Hardened)
# ==============================================================================
[CmdletBinding()]
param(
    [switch]$Interactive
)

$ErrorActionPreference = "Stop"
$RootPath = "G:\AI\E-zzio"
Set-Location $RootPath

$PythonExe = "$RootPath\.venv\Scripts\python.exe"
$StateDir = "$RootPath\runtime\state\backend"
New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

$PidFile = "$StateDir\pid.json"
$HealthFile = "$StateDir\health.json"

function Write-RuntimeManifests {
    param($TargetPid, $Status = "STARTING")
    
    $RuntimeManifest = @{
        service = "ezzio-api"
        pid = $TargetPid
        port = 8001
        started_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    $RuntimeManifest | ConvertTo-Json | Set-Content $PidFile -Encoding UTF8

    $Heartbeat = @{
        service = "ezzio-api"
        pid = $TargetPid
        port = 8001
        status = $Status
        version = "v2.6-autonomic-tactical-core"
        last_heartbeat = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    }
    $Heartbeat | ConvertTo-Json | Set-Content $HealthFile -Encoding UTF8
}

function Invoke-SafePause {
    param([string]$Message = "Appuyez sur Entrée pour quitter...")
    $RealInteractive = ($Interactive -and ($Host.Name -eq "ConsoleHost") -and [Environment]::UserInteractive)
    if ($RealInteractive) {
        Write-Host "`n[OK] $Message" -ForegroundColor Cyan
        Read-Host
    } else {
        Write-Host "[HEADLESS] Exécution autonome (aucun verrou clavier)." -ForegroundColor DarkGray
    }
}

$existingListeners = @(Get-NetTCPConnection -State Listen -LocalPort 8001 -ErrorAction SilentlyContinue)
if ($existingListeners.Count -gt 0) {
    Write-Host "[GUARD] Port 8001 occupé. Validation de l'intégrité..." -ForegroundColor Yellow
    try {
        $check = Invoke-RestMethod "http://127.0.0.1:8001/health" -TimeoutSec 2 -ErrorAction Stop
        if ($check.status -eq "ONLINE" -or $check.ok -eq $true) {
            $activeConn = Get-NetTCPConnection -State Listen -LocalPort 8001 -ErrorAction SilentlyContinue | Select-Object -First 1
            $activePid = if ($activeConn) { $activeConn.OwningProcess } else { 0 }
            Write-Host "[GUARD] Instance active (PID: $activePid). Manifestes synchronisés." -ForegroundColor Green
            Write-RuntimeManifests -TargetPid $activePid -Status "ONLINE"
            Invoke-SafePause "Station de contrôle prête. Appuyez sur Entrée..."
            exit 0
        }
    } catch {
        Write-Host "[GUARD] Port actif mais API muette. Poursuite du déploiement..." -ForegroundColor Red
    }
}

Write-Host "[*] Amorçage souverain du backend E-ZZIO..." -ForegroundColor Cyan
$Process = Start-Process -FilePath $PythonExe -ArgumentList "web_server.py" -WorkingDirectory $RootPath -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 1

$verify = Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -eq $Process.Id -and $_.CommandLine -match "web_server.py" }
if (-not $verify) {
    Write-Error "[FAIL] PID créé mais processus web_server.py introuvable en RAM."
    Invoke-SafePause "Appuyez sur Entrée pour quitter..."
    exit 1
}

Write-RuntimeManifests -TargetPid $Process.Id -Status "STARTING"

Write-Host "[*] Attente de l'écoute effective sur le port 8001..." -ForegroundColor Yellow
$portReady = $false
for ($i = 0; $i -lt 15; $i++) {
    if (Get-NetTCPConnection -State Listen -LocalPort 8001 -ErrorAction SilentlyContinue) {
        $portReady = $true
        break
    }
    Start-Sleep -Seconds 1
}

if (-not $portReady) {
    Write-Error "[FAIL] Aucun listener TCP 8001 détecté dans le délai imparti."
    Invoke-SafePause "Appuyez sur Entrée pour quitter..."
    exit 1
}

Write-Host "[*] Certification de l'API (/health)..." -ForegroundColor Yellow
$timeout = 10; $elapsed = 0; $apiReady = $false
while ($elapsed -lt $timeout) {
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        if ($response.status -eq "ONLINE" -or $response.ok -eq $true) {
            Write-Host "[OK] API E-ZZIO certifiée et ONLINE (PID: $($Process.Id))." -ForegroundColor Green
            Write-RuntimeManifests -TargetPid $Process.Id -Status "ONLINE"
            $apiReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
        $elapsed++
    }
}

if (-not $apiReady) {
    Write-Error "[!] Échec critique : L'API n'a pas répondu au healthcheck."
    Invoke-SafePause "Appuyez sur Entrée pour quitter..."
    exit 1
} else {
    Write-Host "`n[OK] Démarrage et certification terminés avec succès." -ForegroundColor Green
    Invoke-SafePause "Appuyez sur Entrée pour fermer cette fenêtre..."
}
