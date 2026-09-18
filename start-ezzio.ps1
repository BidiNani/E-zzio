<#
.SYNOPSIS
    E-zzio — Démarrage global en une commande.
.DESCRIPTION
    Libère le port backend, lance backend + frontend dans 2 fenêtres,
    attend la réponse des 2 services, ouvre Brave.
.EXAMPLE
    cd G:\AI\E-zzio
    .\start-ezzio.ps1
#>
[CmdletBinding()]
param(
    [string]$Root     = "G:\AI\E-zzio",
    [string]$Desktop  = "G:\AI\ezzio-desktop",
    [int]   $Port     = 8001,
    [int]   $VitePort = 1420,
    [switch]$NoBrowser,
    [switch]$NoBackend,
    [switch]$NoFrontend
)

$ErrorActionPreference = "Stop"

function Step($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }
function OK($t)       { Write-Host "    OK   $t" -ForegroundColor Green }
function Warn($t)     { Write-Host "    WARN $t" -ForegroundColor Yellow }
function Err($t)      { Write-Host "    ERR  $t" -ForegroundColor Red }

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  E-ZZIO — Démarrage" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Cyan

# 1. Libérer le port backend
Step "1/4" "Libération du port $Port"
$netstat = netstat -ano -p TCP 2>$null
$pids = @()
foreach ($line in $netstat) {
    $p = ($line -split '\s+') | Where-Object { $_ -ne '' }
    if ($p.Count -ge 5 -and $p[0] -eq 'TCP' -and $p[3] -eq 'LISTENING' -and $p[1] -match ":$Port$") {
        if ($p[4] -match '^\d+$') { $pids += [int]$p[4] }
    }
}
$pids = $pids | Sort-Object -Unique
if ($pids.Count -eq 0) { OK "Port $Port déjà libre" }
else {
    foreach ($pid_ in $pids) {
        try { Stop-Process -Id $pid_ -Force; Write-Host "    kill PID $pid_" -ForegroundColor DarkGray } catch {}
    }
    Start-Sleep -Milliseconds 800
    OK "Port $Port libéré"
}

# 2. Backend
if ($NoBackend) { Step "2/4" "Backend — sauté" }
else {
    Step "2/4" "Backend"
    $venvPy  = Join-Path $Root ".venv\Scripts\python.exe"
    $backend = Join-Path $Root "web_server.py"
    if (-not (Test-Path $venvPy))  { Err "Python venv introuvable : $venvPy"; exit 1 }
    if (-not (Test-Path $backend)) { Err "web_server.py introuvable : $backend"; exit 1 }

    $cmd = "Set-Location '$Root'; Write-Host 'E-ZZIO Backend' -ForegroundColor Cyan; & '.\.venv\Scripts\python.exe' web_server.py"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd | Out-Null
    Write-Host "    Fenêtre backend ouverte, attente..." -ForegroundColor DarkGray

    $deadline = (Get-Date).AddSeconds(20)
    $up = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-RestMethod "http://127.0.0.1:$Port/health" -TimeoutSec 2
            if ($r.status -eq 'ONLINE') { $up = $true; break }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    if ($up) { OK "Backend ONLINE" } else { Err "Backend injoignable après 20s"; exit 1 }
}

# 3. Frontend
if ($NoFrontend) { Step "3/4" "Frontend — sauté" }
else {
    Step "3/4" "Frontend"
    if (-not (Test-Path (Join-Path $Desktop "package.json"))) { Err "package.json introuvable"; exit 1 }

    $cmd = "Set-Location '$Desktop'; Write-Host 'E-ZZIO Frontend' -ForegroundColor Cyan; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd | Out-Null
    Write-Host "    Fenêtre frontend ouverte, attente..." -ForegroundColor DarkGray

    $deadline = (Get-Date).AddSeconds(20)
    $up = $false
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest "http://localhost:$VitePort/" -TimeoutSec 2 -UseBasicParsing
            if ($r.StatusCode -eq 200) { $up = $true; break }
        } catch {}
        Start-Sleep -Milliseconds 500
    }
    if ($up) { OK "Frontend ONLINE" } else { Err "Frontend injoignable après 20s"; exit 1 }
}

# 4. Brave
if ($NoBrowser) { Step "4/4" "Brave — sauté" }
else {
    Step "4/4" "Brave"
    $url = "http://localhost:$VitePort"
    $bravePaths = @(
        "$env:LOCALAPPDATA\BraveSoftware\Brave-Browser\Application\brave.exe",
        "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        "C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"
    )
    $brave = $bravePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($brave) { Start-Process $brave $url; OK "Brave ouvert sur $url" }
    else { Warn "Brave introuvable — ouvre $url manuellement" }
}

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  E-ZZIO — Démarré" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend  : http://127.0.0.1:$Port" -ForegroundColor White
Write-Host "  Frontend : http://localhost:$VitePort" -ForegroundColor White
Write-Host ""
Write-Host "  2 fenêtres PowerShell sont ouvertes (backend + frontend)" -ForegroundColor Gray
Write-Host "  Ferme ces fenêtres pour arrêter E-zzio" -ForegroundColor Gray
Write-Host ""