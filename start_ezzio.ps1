#requires -Version 5.1
[CmdletBinding()]
param(
    [switch]$SkipInstall,
    [switch]$SkipBuild,
    [switch]$SkipCompile,
    [switch]$NoStopPorts
)

$ErrorActionPreference = "Stop"

$ProjectRoot    = "G:\AI\E-zzio"
$FrontendRoot   = "G:\AI\E-zzio\ezzio-ui"
$PythonExe      = "python.exe" 
$BackendApp     = "web_server:app"

$BackendHost    = "127.0.0.1"
$BackendPort    = 8000
$FrontendPort   = 5173
$OllamaUrl      = "http://127.0.0.1:11434/api/tags"

$BackendUrl     = "http://$BackendHost`:$BackendPort"
$FrontendUrl    = "http://$BackendHost`:$FrontendPort"

$Stamp          = Get-Date -Format "yyyyMMdd_HHmmss"
$LogRoot        = Join-Path $ProjectRoot "logs\start_ezzio_$Stamp"

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null

$env:PYTHONPATH = $ProjectRoot
$env:OLLAMA_NUM_GPU = "0"
$env:CUDA_VISIBLE_DEVICES = ""

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Test-Url {
    param([string]$Url)
    try {
        # On accepte toutes les réponses (même 404), car si le serveur répond 404, c'est qu'il est vivant.
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
        return $true
    } catch {
        return $false
    }
}

function Wait-Url {
    param(
        [string]$Name,
        [string[]]$Urls,
        [int]$TimeoutSec = 90
    )
    $start = Get-Date
    $deadline = $start.AddSeconds($TimeoutSec)
    $tick = 0
    Write-Host ""
    Write-Host "Attente $Name pendant maximum $TimeoutSec secondes..." -ForegroundColor Cyan
    while ((Get-Date) -lt $deadline) {
        foreach ($url in $Urls) {
            if (Test-Url -Url $url) {
                $elapsed = [math]::Round(((Get-Date) - $start).TotalSeconds, 1)
                Write-Host "[OK] $Name prêt en ${elapsed}s : $url" -ForegroundColor Green
                return $true
            }
        }
        $tick++
        if ($tick % 5 -eq 0) {
            $elapsed = [math]::Round(((Get-Date) - $start).TotalSeconds, 0)
            Write-Host "  ... $Name pas encore prêt (${elapsed}s)" -ForegroundColor DarkYellow
        }
        Start-Sleep -Seconds 1
    }
    Write-Host "[FAIL] $Name non prêt après $TimeoutSec secondes" -ForegroundColor Red
    return $false
}

function Stop-Port {
    param([int]$Port, [string]$Name)
    Write-Host ""
    Write-Host "Vérification port $Port pour $Name..."
    $connections = @(Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" })
    if ($connections.Count -eq 0) {
        Write-Host "[OK] Port $Port libre pour $Name" -ForegroundColor Green
        return
    }
    foreach ($connection in $connections) {
        $processId = [int]$connection.OwningProcess
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Host "[OK] PID $processId arrêté" -ForegroundColor Green
        } catch { }
    }
    Start-Sleep -Seconds 2
}

function Start-NewPowerShellWindow {
    param([string]$Title, [string]$WorkingDirectory, [string]$Command)
    $safeTitle = $Title.Replace("'", "''")
    $wrapped = @"
`$Host.UI.RawUI.WindowTitle = '$safeTitle'
`$env:PYTHONPATH = '$ProjectRoot'
`$env:OLLAMA_NUM_GPU = '0'
Set-Location -LiteralPath '$WorkingDirectory'
try { $Command } finally { Read-Host 'Appuie sur Entrée pour fermer' }
"@
    $encoded = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($wrapped))
    Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $encoded -WindowStyle Normal
}

Write-Section "E-zzio - Démarrage Stable"
if (-not $NoStopPorts) {
    Stop-Port -Port $FrontendPort -Name "frontend Svelte"
    Stop-Port -Port $BackendPort -Name "backend FastAPI"
}

Write-Section "Lancement backend FastAPI"
Start-NewPowerShellWindow -Title "E-zzio Backend" -WorkingDirectory $ProjectRoot -Command "& '$PythonExe' -m uvicorn $BackendApp --port $BackendPort"

if (-not (Wait-Url -Name "Backend" -Urls @("$BackendUrl/"))) { exit 1 }

Write-Section "Lancement frontend Svelte"
Start-NewPowerShellWindow -Title "E-zzio Frontend" -WorkingDirectory $FrontendRoot -Command "npm run dev -- --host $BackendHost --port $FrontendPort --open"

Write-Section "Résultat"
Write-Host "[OK] E-zzio est en ligne." -ForegroundColor Green
Read-Host "Appuie sur Entrée pour fermer cette fenêtre"