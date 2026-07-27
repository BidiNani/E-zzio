# Sentinelle Autonome E-zzio - Tracking de Processus & Healthcheck
$ApiProcess = $null
$BotProcess = $null
$DiscordRunning = $false

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   SENTINELLE E-ZZIO : VEILLE SÉCURISÉE   " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

function Stop-Gracefully {
    param([System.Diagnostics.Process]$Proc)
    if ($Proc -and -not $Proc.HasExited) {
        Write-Host "[-] Fermeture gracieuse du PID $($Proc.Id)..." -ForegroundColor Yellow
        $Proc.CloseMainWindow() | Out-Null
        if (-not $Proc.WaitForExit(3000)) {
            Write-Host "    [!] Timeout dépassé, destruction forcée du PID $($Proc.Id)." -ForegroundColor Red
            $Proc.Kill()
        }
    }
}

while ($true) {
    $DiscordProcess = Get-Process Discord -ErrorAction SilentlyContinue
    
    if ($DiscordProcess -and -not $DiscordRunning) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] DÉTECTION : Discord est actif. Armement du Kernel..." -ForegroundColor Green
        $DiscordRunning = $true
        
        Write-Host "    [+] Lancement de l'API Gateway FastAPI..." -ForegroundColor DarkGray
        $ApiProcess = Start-Process -FilePath "python" -ArgumentList "interfaces\api\server.py" -WindowStyle Minimized -PassThru
        
        Start-Sleep -Seconds 4 # Attente de la montée du port 8000
        
        Write-Host "    [+] Lancement du Client Discord E-zzio..." -ForegroundColor DarkGray
        $BotProcess = Start-Process -FilePath "python" -ArgumentList "interfaces\discord\bot.py" -WindowStyle Minimized -PassThru

    } elseif (-not $DiscordProcess -and $DiscordRunning) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] DÉTECTION : Discord est fermé. Désarmement du Kernel..." -ForegroundColor Yellow
        $DiscordRunning = $false
        
        Stop-Gracefully -Proc $BotProcess
        Stop-Gracefully -Proc $ApiProcess
        
        $ApiProcess = $null
        $BotProcess = $null
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Kernel éteint. Retour en veille." -ForegroundColor Green
    }
    
    Start-Sleep -Seconds 5
}
