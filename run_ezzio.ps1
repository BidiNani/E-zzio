# run_ezzio.ps1
Write-Host "Lancement du cerveau (Backend)..." -ForegroundColor Cyan
Start-Process python -ArgumentList "web_server.py" -WindowStyle Hidden

Write-Host "Lancement de l'interface (Frontend)..." -ForegroundColor Green
Start-Process npm -ArgumentList "run dev -- --open" -WorkingDirectory "G:\AI\E-zzio\ezzio-ui" -WindowStyle Hidden

Write-Host "E-zzio est en ligne ! Le serveur tourne en arrière-plan." -ForegroundColor Yellow
Write-Host "Pour arrêter E-zzio, ferme simplement cette fenêtre ou tue les processus Node/Python."