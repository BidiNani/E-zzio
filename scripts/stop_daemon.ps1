Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*bot_runner.py*" } | ForEach-Object { 
    Stop-Process -Id $_.ProcessId -Force 
    Write-Host "[OK] Processus $($_.ProcessId) arrêté." -ForegroundColor Yellow
}
Write-Host "[OK] Tous les services E-ZZIO sont stoppés." -ForegroundColor Green
