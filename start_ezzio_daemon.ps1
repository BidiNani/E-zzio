# ==============================================================================
# E-ZZIO SOVEREIGN DAEMON (WATCHDOG & CLEAN KILL)
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectPath = "G:\AI\E-zzio"

Write-Host "============================================================" -ForegroundColor DarkRed
Write-Host " INITIATION DU DÉMON SOUVERAIN (WATCHDOG ACTIF)" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor DarkRed

function Kill-EzzioProcesses {
    Write-Host "[..] Nettoyage chirurgical des processus existants..." -ForegroundColor Yellow

    $Processes = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
        $_.CommandLine -like "*web_server.py*" -or $_.CommandLine -like "*discord_agent_v2.py*"
    }

    if ($Processes) {
        foreach ($Proc in $Processes) {
            $Id = $Proc.ProcessId
            Write-Host "  -> Exécution de la sentence pour le PID $Id" -ForegroundColor DarkGray
            Stop-Process -Id $Id -Force -ErrorAction SilentlyContinue

            # La règle d'or : on attend la mort réelle et confirmée du processus
            try {
                Wait-Process -Id $Id -Timeout 10 -ErrorAction SilentlyContinue
            } catch {
                Write-Host "  [!] Le processus $Id résiste au-delà du timeout." -ForegroundColor Red
            }
        }
        Write-Host "[OK] Purge terminée. La mémoire est propre." -ForegroundColor Green
    } else {
        Write-Host "[OK] Aucun processus fantôme parasite détecté." -ForegroundColor Green
    }

    # Libération du port 8001 au cas où un socket serait resté ouvert
    try {
        $Conn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
        if ($Conn) {
            Stop-Process -Id $Conn.OwningProcess -Force -ErrorAction SilentlyContinue
            Wait-Process -Id $Conn.OwningProcess -Timeout 5 -ErrorAction SilentlyContinue
        }
    } catch {}
}

# 1. On tue tout ce qui bouge avant de commencer
Kill-EzzioProcesses

# NB : PYTHONPATH doit être réexporté ici, pas seulement Set-Location.
# web_server.py et discord_agent_v2.py s'en passent (Python ajoute déjà le
# dossier du script à sys.path), MAIS tout script lancé en sous-process
# depuis un autre dossier (ex: exec_tools.run_python_script sur un fichier
# dans tools/) a besoin de PYTHONPATH pour résoudre "from core.xxx import ...".
# Sans ça, ces sous-process plantent en ModuleNotFoundError.
$env:PYTHONPATH = $ProjectPath
Set-Location -Path $ProjectPath

Write-Host "[*] Démarrage du Noyau et de l'Agent..." -ForegroundColor Cyan

# 2. Lancement initial avec récupération des objets processus
$WebProcess = Start-Process -FilePath "G:\Python312\python.exe" -ArgumentList "web_server.py" -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 3 # Laisse le temps au serveur Uvicorn de bind le port
$DiscordProcess = Start-Process -FilePath "G:\Python312\python.exe" -ArgumentList "discord_agent_v2.py" -WindowStyle Hidden -PassThru

Write-Host "============================================================" -ForegroundColor DarkRed
Write-Host " SYSTÈME GRAVÉ. SURVEILLANCE ACTIVE. (CTRL+C pour stopper)" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor DarkRed

# 3. Boucle Watchdog de surveillance, avec protection anti-crash-loop :
# si un process meurt en boucle très vite (bug qui ne se résout pas tout
# seul, ex: dépendance manquante), on arrête de le relancer frénétiquement
# et on prévient au lieu de spammer des relances toutes les 5 secondes.
$WebCrashTimes = New-Object System.Collections.Generic.List[datetime]
$DiscordCrashTimes = New-Object System.Collections.Generic.List[datetime]
$MaxCrashesPerWindow = 5
$CrashWindowSeconds = 60

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

        if ($WebProcess.HasExited) {
            if (Test-CrashLoop -CrashTimes $WebCrashTimes) {
                Write-Host "[X] Le Noyau crashe en boucle ($MaxCrashesPerWindow fois en ${CrashWindowSeconds}s). Watchdog en pause pour ce composant — corrige le bug avant de relancer manuellement." -ForegroundColor Magenta
                Start-Sleep -Seconds $CrashWindowSeconds
                $WebCrashTimes.Clear()
                continue
            }
            Write-Host "[!] Crash du Noyau détecté. Relance immédiate de l'architecture..." -ForegroundColor Red
            Kill-EzzioProcesses
            $WebProcess = Start-Process -FilePath "G:\Python312\python.exe" -ArgumentList "web_server.py" -WindowStyle Hidden -PassThru
            Start-Sleep -Seconds 3
            $DiscordProcess = Start-Process -FilePath "G:\Python312\python.exe" -ArgumentList "discord_agent_v2.py" -WindowStyle Hidden -PassThru
        }

        if ($DiscordProcess.HasExited) {
            if (Test-CrashLoop -CrashTimes $DiscordCrashTimes) {
                Write-Host "[X] L'Agent Discord crashe en boucle ($MaxCrashesPerWindow fois en ${CrashWindowSeconds}s). Watchdog en pause pour ce composant." -ForegroundColor Magenta
                Start-Sleep -Seconds $CrashWindowSeconds
                $DiscordCrashTimes.Clear()
                continue
            }
            Write-Host "[!] Crash de l'Agent Discord détecté. Injection d'une nouvelle instance..." -ForegroundColor Red
            $DiscordProcess = Start-Process -FilePath "G:\Python312\python.exe" -ArgumentList "discord_agent_v2.py" -WindowStyle Hidden -PassThru
        }
    }
} finally {
    # 4. Nettoyage absolu si tu fermes la fenêtre ou fais un Ctrl+C
    Write-Host "`n[!] Interruption manuelle. Extinction propre des services." -ForegroundColor Yellow
    Kill-EzzioProcesses
}
