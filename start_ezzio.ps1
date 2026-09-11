$Root = "G:\AI\E-zzio"
$Python = "$Root\.venv\Scripts\python.exe"
Start-Process -FilePath $Python -ArgumentList "-m uvicorn web_server:app --host 0.0.0.0 --port 8001" -WindowStyle Hidden -WorkingDirectory $Root
Start-Process -FilePath $Python -ArgumentList "core/integrations/discord/discord_client.py" -WindowStyle Hidden -WorkingDirectory $Root
