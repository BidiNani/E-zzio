<#
.SYNOPSIS
    Lanceur temps réel de production pour le Bot Discord E-ZZIO.
#>

$ProjectPath = "G:\AI\E-zzio"
$PythonPath = "G:\Python312\python.exe"
$BotEntryPoint = "$ProjectPath\interfaces\discord\bot.py"

Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "      LANCEUR DE PRODUCTION - DISCORD E-ZZIO     " -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

Set-Location $ProjectPath

# TRÈS IMPORTANT : Permet à Python de trouver le paquet 'runtime.*'
$env:PYTHONPATH = $ProjectPath

# Vérification de l'environnement
if (-Not (Test-Path $PythonPath)) {
    Write-Host "[-] Python introuvable : $PythonPath" -ForegroundColor Red
    Read-Host "Appuie sur Entrée pour quitter..." ; exit
}

if (-Not (Test-Path $BotEntryPoint)) {
    Write-Host "[-] Point d'entrée introuvable : $BotEntryPoint" -ForegroundColor Red
    Read-Host "Appuie sur Entrée pour quitter..." ; exit
}

# Recompilation à chaud des modifications
Write-Host "[*] Recompilation à chaud du runtime..." -ForegroundColor Yellow
& $PythonPath -m compileall -q runtime interfaces

Write-Host "`n[+] Démarrage du Bot Discord E-ZZIO (mode unbuffered)..." -ForegroundColor Green
Write-Host "-------------------------------------------------" -ForegroundColor Gray

try {
    # Lancement direct avec capture du flux
    & $PythonPath -u $BotEntryPoint
} catch {
    Write-Host "`n[!] ERREUR DU PROCESSUS PYTHON :" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
}

Write-Host "`n-------------------------------------------------" -ForegroundColor Gray
Write-Host " Processus terminé ou interrompu." -ForegroundColor Gray
Read-Host " Appuie sur Entrée pour fermer cette fenêtre..."
