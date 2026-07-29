param(
    [switch]$NoBrowser,
    [switch]$Restart
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$UiRoot = Join-Path $ProjectRoot "ezzio-ui"
$LogRoot = Join-Path $ProjectRoot ("logs\svelte_ui_silent_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
$PidPath = Join-Path $ProjectRoot "state\svelte_ui.pid"

New-Item -ItemType Directory -Force -Path $LogRoot, (Split-Path -Parent $PidPath) | Out-Null

$env:OLLAMA_NUM_GPU = "0"
$env:CUDA_VISIBLE_DEVICES = ""
$env:GGML_CUDA = "0"
$env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"
$env:EZZIO_NO_ADS = "true"
$env:EZZIO_NO_TRACKING = "true"
$env:EZZIO_NO_SPONSORS = "true"

if (-not (Test-Path -LiteralPath (Join-Path $UiRoot "package.json"))) {
    throw "package.json introuvable : $UiRoot"
}

function Stop-PortOwner {
    param([int]$Port)

    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Listen" } |
        ForEach-Object {
            $ownerProcessId = [int]$_.OwningProcess
            try {
                Stop-Process -Id $ownerProcessId -Force
            } catch {}
        }

    Start-Sleep -Seconds 1
}

function Wait-Ui {
    param([int]$TimeoutSec = 45)

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $res = Invoke-WebRequest "http://127.0.0.1:5173" -Method GET -TimeoutSec 3
            if ($res.StatusCode -eq 200) { return $true }
        } catch {
            Start-Sleep -Milliseconds 700
        }
    }

    return $false
}

if ($Restart) {
    Stop-PortOwner -Port 5173
}

$alreadyOnline = $false
try {
    $res = Invoke-WebRequest "http://127.0.0.1:5173" -Method GET -TimeoutSec 3
    $alreadyOnline = ($res.StatusCode -eq 200)
} catch {}

if ($alreadyOnline) {
    Write-Host "=== E-ZZIO SVELTE UI ===" -ForegroundColor Cyan
    Write-Host "Déjà en ligne : http://127.0.0.1:5173" -ForegroundColor Green
    if (-not $NoBrowser) {
        Start-Process "http://127.0.0.1:5173"
    }
    return
}

$stdout = Join-Path $LogRoot "svelte.stdout.log"
$stderr = Join-Path $LogRoot "svelte.stderr.log"

# Important :
# cmd /c garde npm/vite en vie tant que le serveur tourne,
# mais la fenêtre est masquée par WindowStyle Hidden.
$cmd = '/c npm run dev -- --host 127.0.0.1 --port 5173 > "' + $stdout + '" 2> "' + $stderr + '"'

$process = Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList $cmd `
    -WorkingDirectory $UiRoot `
    -WindowStyle Hidden `
    -PassThru

Set-Content -LiteralPath $PidPath -Value $process.Id -Encoding UTF8

$ready = Wait-Ui -TimeoutSec 60

Write-Host "=== E-ZZIO SVELTE UI SILENT ===" -ForegroundColor Cyan
[pscustomobject]@{
    online = $ready
    pid = $process.Id
    url = "http://127.0.0.1:5173"
    stdout = $stdout
    stderr = $stderr
    hidden_window = $true
}

if (-not $ready) {
    Write-Host "UI non prête. Vérifie stderr :" -ForegroundColor Yellow
    Write-Host $stderr
    exit 1
}

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:5173"
}
