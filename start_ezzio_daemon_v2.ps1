# ==============================================================================
# E-ZZIO SOVEREIGN DAEMON V2.1 (LOGS SÉPARÉS, HTTP HEALTH-CHECK, PID CONTROL)
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- CONFIGURATION ---
$ProjectPath = "G:\AI\E-zzio"
$PythonExe = "G:\Python312\python.exe"
$LogDir = Join-Path $ProjectPath "logs"

# Séparation chirurgicale des flux : l'activité standard d'un côté, le sang de l'autre
$WebOutLog = Join-Path $LogDir "web_server.out.log"
$WebErrLog = Join-Path $LogDir "web_server.err.log"
$DiscordOutLog = Join-Path $LogDir "discord_agent.out.log"
$DiscordErrLog = Join-Path $LogDir "discord_agent.err.log"

$env:PYTHONPATH = $ProjectPath

Write-Host "============================================================" -ForegroundColor DarkRed
Write-Host " INITIATION DU DÉMON SOUVERAIN V2.1 (CHIRURGICAL & MONITORÉ)" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor DarkRed

# --- PRÉPARATION DES FONDATIONS ---
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
    Write-Host "[*] Dossier de logs créé : $LogDir" -ForegroundColor DarkGray
}

# --- FONCTIONS SYSTÈME ---
function Test-NoyauHealth {
    try {
        $Response = Invoke-RestMethod -Uri "http://127.0.0.1:8001/health" -Method Get -TimeoutSec 2 -ErrorAction Stop
        if ($Response.status -eq "online") { return $true }
        return $false
    } catch {
        return $false
    }
}

function Stop-EzzioProcess {
    param([System.Diagnostics.Process]$Proc, [string]$Name)
    
    if ($null -eq $Proc -or $Proc.HasExited) { return }
    
    $Id = $Proc.Id
    Write-Host "[..] Tentative d'arrêt gracieux pour $Name (PID: $Id)..." -ForegroundColor Yellow
    
    $Proc.CloseMainWindow() | Out-Null
    
    try {
        if (-not $Proc.WaitForExit(3000)) {
            Write-Host "[!] $Name résiste. Exécution forcée (Kill)." -ForegroundColor Red
            Stop-Process -Id $Id -Force -ErrorAction SilentlyContinue
            Wait-Process -Id $Id -Timeout 5 -ErrorAction SilentlyContinue
        } else {
            Write-Host "[OK] $Name s'est éteint proprement." -ForegroundColor Green
        }
    } catch {
        Write-Host "[X] Erreur lors de l'arrêt de $Name." -ForegroundColor Magenta
    }
}

# --- LANCEMENT INITIAL ---
Write-Host "[*] Démarrage des processus (Logs redirigés)..." -ForegroundColor Cyan
Set-Location -Path $ProjectPath

try {
    $Conn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
    if ($Conn) { Stop-Process -Id $Conn.OwningProcess -Force -ErrorAction SilentlyContinue }
} catch {}

$WebProcess = Start-Process -FilePath $PythonExe -ArgumentList "-u web_server.py" -WindowStyle Hidden -RedirectStandardOutput $WebOutLog -RedirectStandardError $WebErrLog -PassThru
Start-Sleep -Seconds 3
$DiscordProcess = Start-Process -FilePath $PythonExe -ArgumentList "-u discord_agent_v2.py" -WindowStyle Hidden -RedirectStandardOutput $DiscordOutLog -RedirectStandardError $DiscordErrLog -PassThru

Write-Host "  -> Noyau accroché au PID $($WebProcess.Id)" -ForegroundColor DarkGray
Write-Host "  -> Agent accroché au PID $($DiscordProcess.Id)" -ForegroundColor DarkGray

Write-Host "============================================================" -ForegroundColor DarkRed
Write-Host " SYSTÈME SÉCURISÉ. SURVEILLANCE ACTIVE. (CTRL+C pour stopper)" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor DarkRed

# --- BOUCLE WATCHDOG (MONITORING ACTIF) ---
$MaxCrashesPerWindow = 5
$CrashWindowSeconds = 60
$WebCrashTimes = New-Object System.Collections.Generic.List[datetime]
$DiscordCrashTimes = New-Object System.Collections.Generic.List[datetime]

function Test-CrashLoop {
    param([System.Collections.Generic.List[datetime]]$CrashTimes)
    $now = Get-Date
    $CrashTimes.Add($now)
    $CrashTimes.RemoveAll({ param($t) ($now - $t).TotalSeconds -gt $CrashWindowSeconds }) | Out-Null
    return $CrashTimes.Count -ge $MaxCrashesPerWindow
}

try {
    while ($true) {
        Start-Sleep -Seconds 5
        
        $WebDead = $WebProcess.HasExited
        $WebSick = -not $WebDead -and -not (Test-NoyauHealth)
        
        # 1. Vérification du Noyau
        if ($WebDead -or $WebSick) {
            if (Test-CrashLoop -CrashTimes $WebCrashTimes) {
                Write-Host "[X] Le Noyau est en boucle d'erreur fatale. Watchdog en pause (Consulte $WebErrLog)." -ForegroundColor Magenta
                Start-Sleep -Seconds $CrashWindowSeconds
                $WebCrashTimes.Clear()
                continue
            }
            
            $Raison = if ($WebDead) { "Crash détecté" } else { "Health-check HTTP échoué (Deadlock)" }
            Write-Host "[!] $Raison sur le Noyau. Relance chirurgicale..." -ForegroundColor Red
            
            if ($WebSick) { Stop-EzzioProcess -Proc $WebProcess -Name "Noyau Figé" }
            $WebProcess = Start-Process -FilePath $PythonExe -ArgumentList "-u web_server.py" -WindowStyle Hidden -RedirectStandardOutput $WebOutLog -RedirectStandardError $WebErrLog -PassThru
            Start-Sleep -Seconds 3
        }

        # 2. Vérification de l'Agent Discord
        if ($DiscordProcess.HasExited) {
            if (Test-CrashLoop -CrashTimes $DiscordCrashTimes) {
                Write-Host "[X] L'Agent Discord est en boucle d'erreur fatale. Watchdog en pause (Consulte $DiscordErrLog)." -ForegroundColor Magenta
                Start-Sleep -Seconds $CrashWindowSeconds
                $DiscordCrashTimes.Clear()
                continue
            }
            
            Write-Host "[!] Crash de l'Agent Discord détecté. Relance..." -ForegroundColor Red
            $DiscordProcess = Start-Process -FilePath $PythonExe -ArgumentList "-u discord_agent_v2.py" -WindowStyle Hidden -RedirectStandardOutput $DiscordOutLog -RedirectStandardError $DiscordErrLog -PassThru
        }
    }
} finally {
    # --- NETTOYAGE ABSOLU ---
    Write-Host "`n[!] Interruption manuelle. Extinction chirurgicale des processus ciblés." -ForegroundColor Yellow
    Stop-EzzioProcess -Proc $WebProcess -Name "Noyau (web_server.py)"
    Stop-EzzioProcess -Proc $DiscordProcess -Name "Agent Discord (discord_agent_v2.py)"
}