Set-Location "G:\AI\E-zzio"
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*uvicorn*" -or $_.CommandLine -like "*bot_runner.py*" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Milliseconds 1500
if (!(Test-Path "runtime/logs")) { New-Item -ItemType Directory -Path "runtime/logs" | Out-Null }
$PythonPath = Join-Path $PWD ".venv\Scripts\python.exe"
$BotPath = Join-Path $PWD "runtime\discord\bot_runner.py"
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-Command", "$PythonPath -m uvicorn interfaces.api.server:app --host 127.0.0.1 --port 8001 > runtime/logs/api.log 2>&1"
Start-Process powershell -WindowStyle Hidden -ArgumentList "-NoProfile", "-Command", "$PythonPath $BotPath > runtime/logs/discord.log 2>&1"
Write-Host "[OK] Services relancés en daemon." -ForegroundColor Green
