# Sentinelle E-zzio - Optimisée PowerShell (Basse consommation CPU)
$DiscordRunning = $false

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "    SENTINELLE E-ZZIO EN SURVEILLANCE     " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

while ($true) {
    $Process = Get-Process Discord -ErrorAction SilentlyContinue
    
    if ($Process -and -not $DiscordRunning) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ACTION : Discord détecté. Allumage de l'API et du Bot E-zzio..." -ForegroundColor Green
        $DiscordRunning = $true
        
        # Lancement asynchrone du cerveau FastAPI et du Bot
        Start-Process -FilePath "python" -ArgumentList "interfaces\api\server.py" -WindowStyle Minimized -PassThru
        Start-Sleep -Seconds 3 # Laisser le temps à l'API de s'allumer
        Start-Process -FilePath "python" -ArgumentList "interfaces\discord\bot.py" -WindowStyle Minimized -PassThru
        
    } elseif (-not $Process -and $DiscordRunning) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] ACTION : Discord fermé. Extinction des systèmes E-zzio..." -ForegroundColor Yellow
        $DiscordRunning = $false
        
        # Extinction propre des processus Python associés à E-zzio
        Get-WmiObject Win32_Process -Filter "name='python.exe' and CommandLine like '%interfaces%'" | ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force
        }
    }
    
    # Pause intelligente de 5 secondes (Évite de consommer 100% du CPU contrairement à une boucle batch pure)
    Start-Sleep -Seconds 5
}
