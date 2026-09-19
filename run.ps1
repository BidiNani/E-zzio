# ============================================================================
# run.ps1 — Lanceur canonique E-ZzIO (backend web_server:app)
# ============================================================================
param(
    [int]$Port = 8001,
    [switch]$NoReload
)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Py   = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
    Write-Host "[run.ps1] Python venv introuvable : $Py" -ForegroundColor Red
    exit 1
}

# Tue les écouteurs sur le port
Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object {
        try { Stop-Process -Id $_.OwningProcess -Force -ErrorAction Stop } catch {}
    }
Start-Sleep -Milliseconds 400

Set-Location $Root
$uvArgs = @("-m", "uvicorn", "web_server:app", "--host", "127.0.0.1", "--port", "$Port")
if (-not $NoReload) { $uvArgs += "--reload" }

Write-Host "[run.ps1] Démarrage : $Py $($uvArgs -join ' ')" -ForegroundColor Cyan
& $Py @uvArgs
