$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$PythonExe   = "G:\AI\Bidi_BrotherEye-env\Scripts\python.exe"
$Port        = 8000
$HostName    = "127.0.0.1"
$Stamp       = Get-Date -Format "yyyyMMdd_HHmmss"
$LogRoot     = Join-Path $ProjectRoot "logs\manual_start_$Stamp"

$env:PYTHONPATH = $ProjectRoot
$env:OLLAMA_NUM_GPU = "0"
$env:CUDA_VISIBLE_DEVICES = ""
$env:GGML_CUDA = "0"
$env:EZZIO_GPU_POLICY = "disabled_for_ezzio"
$env:EZZIO_NUM_GPU = "0"

New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null

Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    ForEach-Object {
        $ownerProcessId = [int]$_.OwningProcess
        Stop-Process -Id $ownerProcessId -Force -ErrorAction SilentlyContinue
    }

$Stdout = Join-Path $LogRoot "uvicorn.stdout.log"
$Stderr = Join-Path $LogRoot "uvicorn.stderr.log"

$p = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList @("-m", "uvicorn", "web_server:app", "--host", $HostName, "--port", "$Port", "--workers", "1") `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $Stdout `
    -RedirectStandardError $Stderr `
    -WindowStyle Hidden `
    -PassThru

Write-Host "E-ZZIO lancé : http://127.0.0.1:8000"
Write-Host "PID : $($p.Id)"
Write-Host "Logs : $LogRoot"
