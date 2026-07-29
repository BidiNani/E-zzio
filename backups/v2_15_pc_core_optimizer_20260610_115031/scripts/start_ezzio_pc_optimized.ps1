param(
    [switch]$Warmup,
    [switch]$Bench
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$ScriptsRoot = Join-Path $ProjectRoot "scripts"

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
$env:EZZIO_PC_PROFILE = "ryzen_5900x_32gb_cpu_first"
$env:EZZIO_OLLAMA_THREADS_FAST = "8"
$env:EZZIO_OLLAMA_THREADS_NORMAL = "12"
$env:EZZIO_OLLAMA_THREADS_DEEP = "16"

& (Join-Path $ScriptsRoot "restart_ezzio_all.ps1")

try {
    $apiPid = (Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Listen" } |
        Select-Object -First 1 -ExpandProperty OwningProcess)

    if ($apiPid) {
        $p = Get-Process -Id $apiPid -ErrorAction Stop
        $p.PriorityClass = "AboveNormal"
        Write-Host "✅ Priorité API : AboveNormal PID=$apiPid" -ForegroundColor Green
    }
}
catch {
    Write-Warning "Priorité API non modifiée : $($_.Exception.Message)"
}

Invoke-RestMethod "http://127.0.0.1:8000/performance/status" -Method GET -TimeoutSec 30

if ($Warmup) {
    & (Join-Path $ScriptsRoot "warmup_ezzio_pc.ps1") -Level fast
}

if ($Bench) {
    & (Join-Path $ScriptsRoot "bench_ezzio_pc.ps1")
}
