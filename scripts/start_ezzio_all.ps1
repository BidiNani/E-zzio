param(
    [switch]$Lan,
    [switch]$OpenFirewall,
    [switch]$StartComfy
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$PythonExe = "G:\AI\Bidi_BrotherEye-env\Scripts\python.exe"
$ComfyRoot = "G:\AI\external\ComfyUI"
$ComfyPy = Join-Path $ComfyRoot ".venv\Scripts\python.exe"

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogRoot = Join-Path $ProjectRoot "logs\start_all_$Stamp"
$RunRoot = Join-Path $ProjectRoot "state\run"

New-Item -ItemType Directory -Force -Path $LogRoot, $RunRoot | Out-Null

$env:PYTHONPATH = $ProjectRoot
$env:OLLAMA_NUM_GPU = "0"
$env:CUDA_VISIBLE_DEVICES = ""
$env:GGML_CUDA = "0"
$env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"
$env:PYTORCH_ENABLE_MPS_FALLBACK = "0"
$env:EZZIO_NO_ADS = "true"
$env:EZZIO_NO_TRACKING = "true"
$env:EZZIO_NO_SPONSORS = "true"

function Get-EzzioLanIPs {
    $ips = New-Object System.Collections.Generic.List[string]

    try {
        $interfaces = [System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() |
            Where-Object {
                $_.OperationalStatus -eq [System.Net.NetworkInformation.OperationalStatus]::Up -and
                $_.NetworkInterfaceType -ne [System.Net.NetworkInformation.NetworkInterfaceType]::Loopback -and
                $_.NetworkInterfaceType -ne [System.Net.NetworkInformation.NetworkInterfaceType]::Tunnel
            }

        foreach ($iface in $interfaces) {
            foreach ($addr in $iface.GetIPProperties().UnicastAddresses) {
                $ip = [string]$addr.Address.IPAddressToString

                if ($ip -match '^\d{1,3}(\.\d{1,3}){3}$' -and
                    $ip -notlike '127.*' -and
                    $ip -notlike '169.254.*' -and
                    $ip -ne '0.0.0.0') {
                    $ips.Add($ip)
                }
            }
        }
    }
    catch {}

    try {
        $netIps = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object {
                $_.IPAddress -match '^\d{1,3}(\.\d{1,3}){3}$' -and
                $_.IPAddress -notlike '127.*' -and
                $_.IPAddress -notlike '169.254.*' -and
                $_.IPAddress -ne '0.0.0.0' -and
                $_.AddressState -eq 'Preferred'
            } |
            Select-Object -ExpandProperty IPAddress

        foreach ($ip in $netIps) {
            if ($ip) { $ips.Add([string]$ip) }
        }
    }
    catch {}

    $clean = @(
        $ips |
            Where-Object {
                $_ -and
                $_.Trim().Length -gt 0 -and
                $_ -match '^\d{1,3}(\.\d{1,3}){3}$'
            } |
            Sort-Object -Unique
    )

    $preferred = @(
        $clean | Where-Object { $_ -like '192.168.*' -or $_ -like '10.*' -or $_ -like '172.16.*' -or $_ -like '172.17.*' -or $_ -like '172.18.*' -or $_ -like '172.19.*' -or $_ -like '172.2*' -or $_ -like '172.30.*' -or $_ -like '172.31.*' }
    )

    if ($preferred.Count -gt 0) {
        return $preferred
    }

    return $clean
}

function Test-Url {
    param([string]$Url, [int]$TimeoutSec = 3)
    try {
        Invoke-RestMethod $Url -Method GET -TimeoutSec $TimeoutSec | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Stop-PortOwner {
    param([int]$Port)

    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Listen" } |
        ForEach-Object {
            $ownerProcessId = [int]$_.OwningProcess
            Stop-Process -Id $ownerProcessId -Force -ErrorAction SilentlyContinue
        }

    Start-Sleep -Seconds 2
}

function Wait-Url {
    param([string]$Url, [int]$TimeoutSec = 90)

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url $Url 3) { return $true }
        Start-Sleep -Milliseconds 800
    }

    return $false
}

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

        Write-Host "✅ Firewall privé ouvert pour port 8000." -ForegroundColor Green
    }
    catch {
        Write-Warning "Firewall non modifié : $($_.Exception.Message)"
    }
}

Write-Host ""
Write-Host "=== START E-ZZIO ALL ===" -ForegroundColor Cyan
Write-Host "Mode LAN  : $Lan"
Write-Host "ComfyUI   : $StartComfy"
Write-Host "Logs      : $LogRoot"
Write-Host ""

Stop-PortOwner -Port 8000

$HostArg = if ($Lan) { "0.0.0.0" } else { "127.0.0.1" }

$ApiStdout = Join-Path $LogRoot "api.stdout.log"
$ApiStderr = Join-Path $LogRoot "api.stderr.log"

$ApiProcess = Start-Process `
    -FilePath $PythonExe `
    -ArgumentList @("-m", "uvicorn", "web_server:app", "--host", $HostArg, "--port", "8000", "--workers", "1") `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $ApiStdout `
    -RedirectStandardError $ApiStderr `
    -WindowStyle Hidden `
    -PassThru

$ApiProcess.Id | Set-Content -LiteralPath (Join-Path $RunRoot "api.pid") -Encoding ASCII

if (-not (Wait-Url "http://127.0.0.1:8000/router-status" 90)) {
    Write-Host "❌ API non prête. stderr :" -ForegroundColor Red
    Get-Content -LiteralPath $ApiStderr -Tail 120 -ErrorAction SilentlyContinue
    throw "API non prête."
}

Write-Host "✅ API E-ZZIO prête : http://127.0.0.1:8000" -ForegroundColor Green

if ($StartComfy) {
    if (Test-Url "http://127.0.0.1:8188/system_stats" 3) {
        Write-Host "✅ ComfyUI déjà online." -ForegroundColor Green
    }
    else {
        if (-not (Test-Path -LiteralPath $ComfyPy)) {
            Write-Warning "ComfyUI non installé : $ComfyPy"
        }
        else {
            $ComfyStdout = Join-Path $LogRoot "comfy.stdout.log"
            $ComfyStderr = Join-Path $LogRoot "comfy.stderr.log"

            $ComfyProcess = Start-Process `
                -FilePath $ComfyPy `
                -ArgumentList @("main.py", "--listen", "127.0.0.1", "--port", "8188", "--cpu") `
                -WorkingDirectory $ComfyRoot `
                -RedirectStandardOutput $ComfyStdout `
                -RedirectStandardError $ComfyStderr `
                -WindowStyle Hidden `
                -PassThru

            $ComfyProcess.Id | Set-Content -LiteralPath (Join-Path $RunRoot "comfy.pid") -Encoding ASCII

            if (Wait-Url "http://127.0.0.1:8188/system_stats" 180) {
                Write-Host "✅ ComfyUI CPU-only prête : http://127.0.0.1:8188" -ForegroundColor Green
            }
            else {
                Write-Warning "ComfyUI n'a pas répondu. stderr : $ComfyStderr"
            }
        }
    }
}

$status = Invoke-RestMethod "http://127.0.0.1:8000/supervisor/watchdog" -Method GET -TimeoutSec 90

Write-Host ""
Write-Host "Watchdog :" -ForegroundColor Cyan
$status.actions | ForEach-Object { Write-Host "- $_" }

if ($Lan) {
    $ips = @(Get-EzzioLanIPs)

    Write-Host ""
    Write-Host "URLs smartphone possibles :" -ForegroundColor Cyan

    if ($ips.Count -eq 0) {
        Write-Warning "Aucune IP LAN détectée."
        Write-Host "Essaie manuellement : http://192.168.1.10:8000/supervisor/mobile-home" -ForegroundColor Yellow
    }
    else {
        foreach ($ip in $ips) {
            if ($ip -and $ip.Trim().Length -gt 0) {
                Write-Host "http://$ip:8000/supervisor/mobile-home"
                Write-Host "http://$ip:8000/status"
                Write-Host "http://$ip:8000/omni-bridge/mobile/config"
                Write-Host ""
            }
        }
    }
}
