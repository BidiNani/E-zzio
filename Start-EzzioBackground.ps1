$ProjectPath = "G:\AI\E-zzio"
$PythonPath = "G:\Python312\python.exe"
$env:PYTHONPATH = $ProjectPath
Set-Location $ProjectPath

# 1. Lancement du Cerveau (API Gateway web_server.py) en arrière-plan
Write-Host "[*] Lancement de l'API Gateway (web_server.py)..."
$ApiProcess = Start-Process -FilePath $PythonPath -ArgumentList "-u web_server.py" -WorkingDirectory $ProjectPath -PassThru -WindowStyle Hidden

# Petite pause pour laisser le temps à l'API de s'initialiser sur le port 8000
Start-Sleep -Seconds 3

# 2. Lancement de la Bouche (Bot Discord bot.py) en arrière-plan
Write-Host "[*] Lancement du Bot Discord..."
$BotProcess = Start-Process -FilePath $PythonPath -ArgumentList "-u interfaces\discord\bot.py" -WorkingDirectory $ProjectPath -PassThru -WindowStyle Hidden

# Boucle de surveillance active pour maintenir le script en vie
while ($true) {
    if ($ApiProcess.HasExited) {
        Write-Host "[!] L'API Gateway s'est arrêtée. Redémarrage..."
        $ApiProcess = Start-Process -FilePath $PythonPath -ArgumentList "-u web_server.py" -WorkingDirectory $ProjectPath -PassThru -WindowStyle Hidden
    }
    if ($BotProcess.HasExited) {
        Write-Host "[!] Le Bot Discord s'est arrêté. Redémarrage..."
        $BotProcess = Start-Process -FilePath $PythonPath -ArgumentList "-u interfaces\discord\bot.py" -WorkingDirectory $ProjectPath -PassThru -WindowStyle Hidden
    }
    Start-Sleep -Seconds 10
}
