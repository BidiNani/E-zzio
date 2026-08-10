# ==============================================================================
# E-ZZIO DIAGNOSTIC CRASH CAPTURE (.PS1)
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectPath = "G:\AI\E-zzio"
$PythonPath = "G:\Python312\python.exe"
$env:PYTHONPATH = $ProjectPath
Set-Location $ProjectPath

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " LANCEMENT DIAGNOSTIQUE DE WEB_SERVER.PY (PREMIER PLAN)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Nettoyage préalable
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { 
    $_.CommandLine -like "*web_server.py*" 
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

try {
    $conn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
    if ($conn) { Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue }
} catch {}

Write-Host "[..] Exécution directe pour capturer l'erreur Python..." -ForegroundColor Yellow
& $PythonPath -u "$ProjectPath\web_server.py"