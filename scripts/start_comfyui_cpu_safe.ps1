$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ============================================================
# E-ZZIO - START COMFYUI CPU/RAM ONLY
# Intelligent : ne relance pas si ComfyUI tourne déjà.
# ============================================================

$ComfyRoot = "G:\AI\external\ComfyUI"
$ComfyPy = Join-Path $ComfyRoot ".venv\Scripts\python.exe"
$ComfyUrl = "http://127.0.0.1:8188"
$Port = 8188

if (-not (Test-Path -LiteralPath $ComfyPy)) {
    throw "ComfyUI non installé. Lance : G:\AI\E-zzio\scripts\install_comfyui_cpu.ps1"
}

$existing = @(
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" }
)

if ($existing.Count -gt 0) {
    Write-Host ""
    Write-Host "✅ ComfyUI semble déjà lancé sur $ComfyUrl" -ForegroundColor Green

    foreach ($connection in $existing) {
        $ownerProcessId = [int]$connection.OwningProcess
        try {
            $process = Get-Process -Id $ownerProcessId -ErrorAction Stop
            Write-Host "PID : $ownerProcessId / $($process.ProcessName)"
        }
        catch {
            Write-Host "PID : $ownerProcessId"
        }
    }

    try {
        $health = Invoke-RestMethod "$ComfyUrl/system_stats" -Method GET -TimeoutSec 3
        Write-Host "Health : OK" -ForegroundColor Green
    }
    catch {
        Write-Warning "Port occupé, mais health ComfyUI indisponible : $($_.Exception.Message)"
    }

    Write-Host ""
    Write-Host "Pour redémarrer proprement :"
    Write-Host "G:\AI\E-zzio\scripts\stop_comfyui.ps1"
    Write-Host "G:\AI\E-zzio\scripts\start_comfyui_cpu_safe.ps1"
    return
}

$env:CUDA_VISIBLE_DEVICES = ""
$env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
$env:OLLAMA_NUM_GPU = "0"
$env:GGML_CUDA = "0"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"
$env:PYTORCH_ENABLE_MPS_FALLBACK = "0"

Set-Location -LiteralPath $ComfyRoot

Write-Host ""
Write-Host "=== COMFYUI CPU/RAM ONLY ===" -ForegroundColor Cyan
Write-Host "URL : $ComfyUrl"
Write-Host "GPU : masqué / --cpu forcé"
Write-Host ""

& $ComfyPy "main.py" "--listen" "127.0.0.1" "--port" "$Port" "--cpu"
