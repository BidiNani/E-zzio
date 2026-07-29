$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"

$env:OLLAMA_NUM_GPU = "0"
$env:CUDA_VISIBLE_DEVICES = ""
$env:GGML_CUDA = "0"
$env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"
$env:EZZIO_NO_ADS = "true"
$env:EZZIO_NO_TRACKING = "true"
$env:EZZIO_NO_SPONSORS = "true"

Write-Host "=== E-ZZIO DESKTOP START ===" -ForegroundColor Cyan

& (Join-Path $ProjectRoot "scripts\restart_ezzio_all.ps1")
& (Join-Path $ProjectRoot "scripts\start_svelte_ui.ps1")
