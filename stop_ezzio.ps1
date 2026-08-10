# ==============================================================================
# E-ZZIO STOP DAEMON (.PS1)
# ==============================================================================
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { 
    $_.CommandLine -like "*web_server.py*" -or $_.CommandLine -like "*discord_agent_v2.py*" 
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Processus arrêté (ID: $($_.ProcessId))" -ForegroundColor Green
}