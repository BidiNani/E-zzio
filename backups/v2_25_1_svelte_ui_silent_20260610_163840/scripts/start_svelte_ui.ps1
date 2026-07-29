$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$UiRoot = Join-Path $ProjectRoot "ezzio-ui"
$LogRoot = Join-Path $ProjectRoot ("logs\svelte_ui_" + (Get-Date -Format "yyyyMMdd_HHmmss"))

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null

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

try {
    Invoke-RestMethod "http://127.0.0.1:8000/status" -Method GET -TimeoutSec 5 | Out-Null
}
catch {
    Write-Host "API backend non joignable. Lance d'abord restart_ezzio_all.ps1." -ForegroundColor Yellow
}

Set-Location -LiteralPath $UiRoot

Write-Host "=== E-ZZIO SVELTE UI ===" -ForegroundColor Cyan
Write-Host "UI : http://127.0.0.1:5173"
Write-Host "Logs : $LogRoot"

Start-Process `
    -FilePath "cmd.exe" `
    -ArgumentList "/k npm run dev -- --host 127.0.0.1 --port 5173" `
    -WorkingDirectory $UiRoot

Start-Sleep -Seconds 3
Start-Process "http://127.0.0.1:5173"
