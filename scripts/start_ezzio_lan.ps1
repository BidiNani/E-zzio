$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

param(
    [switch]$OpenFirewall
)

# ============================================================
# E-ZZIO - Start LAN for smartphone
# Lance E-ZZIO sur 0.0.0.0:8001 pour accès Wi-Fi local.
# Token requis sur endpoints mobile sensibles.
# ============================================================

$ProjectRoot = "G:\AI\E-zzio"
$PythonExe = "G:\AI\Bidi_BrotherEye-env\Scripts\python.exe"
$LogRoot = Join-Path $ProjectRoot ("logs\lan_start_" + (Get-Date -Format "yyyyMMdd_HHmmss"))

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null

$env:PYTHONPATH = $ProjectRoot
$env:OLLAMA_NUM_GPU = "0"
$env:CUDA_VISIBLE_DEVICES = ""
$env:GGML_CUDA = "0"
$env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"
$env:EZZIO_NO_ADS = "true"
$env:EZZIO_NO_TRACKING = "true"
$env:EZZIO_NO_SPONSORS = "true"

if ($OpenFirewall) {
    try {
        New-NetFirewallRule `
            -DisplayName "E-ZZIO Local API 8000" `
            -Direction Inbound `
            -Action Allow `
            -Protocol TCP `
            -LocalPort 8000 `
            -Profile Private `
            -ErrorAction SilentlyContinue | Out-Null

        Write-Host "✅ Règle firewall privée ajoutée pour port 8000." -ForegroundColor Green
    }
    catch {
        Write-Warning "Firewall non modifié : $($_.Exception.Message)"
    }
}

Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    ForEach-Object {
        $ownerProcessId = [int]$_.OwningProcess
        Stop-Process -Id $ownerProcessId -Force -ErrorAction SilentlyContinue
    }

Start-Sleep -Seconds 2

$stdout = Join-Path $LogRoot "uvicorn_lan.stdout.log"
$stderr = Join-Path $LogRoot "uvicorn_lan.stderr.log"

$process = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList @("-m", "uvicorn", "web_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1") `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -WindowStyle Hidden `
    -PassThru

Start-Sleep -Seconds 4

$ips = @()
try {
    $ips = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -ExpandProperty IPAddress
}
catch {}

Write-Host ""
Write-Host "✅ E-ZZIO LAN démarré." -ForegroundColor Green
Write-Host "PID    : $($process.Id)"
Write-Host "Logs   : $LogRoot"
Write-Host "stderr : $stderr"
Write-Host ""
Write-Host "URLs possibles smartphone même Wi-Fi :" -ForegroundColor Cyan
foreach ($ip in $ips) {
    Write-Host "http://$ip:8001/status"
    Write-Host "http://$ip:8001/omni-bridge/mobile/config"
}
Write-Host ""
Write-Host "Si ton téléphone ne se connecte pas : relance avec -OpenFirewall."

