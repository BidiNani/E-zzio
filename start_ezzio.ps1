# Attente de la stabilisation réseau au démarrage
Start-Sleep -Seconds 5
Set-Location "G:\AI\E-zzio"

# Nettoyage préventif des anciens processus Python résiduels
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Lancement du serveur FastAPI (port 8001) en mode masqué
Start-Process "G:\Python312\python.exe" -ArgumentList "web_server.py" -WindowStyle Hidden

# Pause pour laisser le temps au serveur web de s'initialiser et libérer le socket
Start-Sleep -Seconds 3

# Lancement du Bot Discord en mode masqué
Start-Process "G:\Python312\python.exe" -ArgumentList "interfaces/discord/bot.py" -WindowStyle Hidden
