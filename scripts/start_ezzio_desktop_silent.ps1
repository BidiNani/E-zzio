param(
    [switch]$NoBrowser,
    [switch]$RestartUi
)

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

Write-Host "=== E-ZZIO DESKTOP SILENT START ===" -ForegroundColor Cyan

# Backend : utilise le script existant. Il est déjà majoritairement silencieux côté API.
& (Join-Path $ProjectRoot "scripts\restart_ezzio_all.ps1")

# Frontend : nouveau mode hidden.
if ($RestartUi) {
    & (Join-Path $ProjectRoot "scripts\start_svelte_ui.ps1") -Restart -NoBrowser:$NoBrowser
} else {
    & (Join-Path $ProjectRoot "scripts\start_svelte_ui.ps1") -NoBrowser:$NoBrowser
}
