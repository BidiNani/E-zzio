$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ComfyRoot = "G:\AI\external\ComfyUI"
$Py = Join-Path $ComfyRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Py)) {
    throw "ComfyUI non installé. Lance : G:\AI\E-zzio\scripts\install_comfyui_cpu.ps1"
}

$env:CUDA_VISIBLE_DEVICES = ""
$env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
$env:OLLAMA_NUM_GPU = "0"
$env:GGML_CUDA = "0"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"
$env:PYTORCH_ENABLE_MPS_FALLBACK = "0"

Set-Location -LiteralPath $ComfyRoot

Write-Host "ComfyUI CPU-only : http://127.0.0.1:8188" -ForegroundColor Cyan
Write-Host "GPU masqué. Mode --cpu forcé." -ForegroundColor Yellow

& $Py "main.py" "--listen" "127.0.0.1" "--port" "8188" "--cpu"
