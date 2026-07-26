@echo off
title Sentinelle E-zzio (Mode Debug)
cd /d G:\AI\E-zzio

echo ==========================================
echo    SENTINELLE E-ZZIO EN SURVEILLANCE
echo ==========================================

:ATTENTE_OUVERTURE
:: L'étoile (*) permet de détecter n'importe quelle version de Discord
tasklist /FI "IMAGENAME eq Discord*" 2>NUL | find /I "Discord">NUL
if "%ERRORLEVEL%"=="0" (
    echo [ACTION] Discord est ouvert ! Allumage du bot E-zzio...
    start "" "G:\AI\E-zzio\Demarrer_Ezzio.bat"
    timeout /t 5 /nobreak > NUL
    goto ATTENTE_FERMETURE
) else (
    timeout /t 3 /nobreak > NUL
    goto ATTENTE_OUVERTURE
)

:ATTENTE_FERMETURE
tasklist /FI "IMAGENAME eq Discord*" 2>NUL | find /I "Discord">NUL
if "%ERRORLEVEL%"=="1" (
    echo [ACTION] Discord a ete ferme. Extinction du bot...
    taskkill /FI "WINDOWTITLE eq E-zzio - DISCORD*" /F /T >NUL 2>&1
    timeout /t 2 /nobreak > NUL
    goto ATTENTE_OUVERTURE
) else (
    timeout /t 3 /nobreak > NUL
    goto ATTENTE_FERMETURE
)
