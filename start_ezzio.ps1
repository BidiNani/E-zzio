$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$PythonExe   = "$ProjectRoot\.venv\Scripts\python.exe"
$Port        = 8001
$HealthUrl   = "http://127.0.0.1:$Port/health"

function Test-BackendHealth {
    try {
        $resp = Invoke-RestMethod -Uri $HealthUrl -Method GET -TimeoutSec 3 -ErrorAction Stop
        if ($resp -and ($resp.ok -eq $true -or $resp.status -eq "ONLINE")) {
            return $true
        }
    } catch {
        return $false
    }
    return $false
}

# 1. Verification Backend web_server (single-instance)
if (Test-BackendHealth) {
    Write-Host "[LAUNCHER] Backend web_server is ALREADY running and healthy on port $Port. Reusing existing instance." -ForegroundColor Green
} else {
    Write-Host "[LAUNCHER] Backend web_server is offline. Starting new instance on port $Port..." -ForegroundColor Yellow
    $cmd = "`"$PythonExe`" -m uvicorn web_server:app --host 127.0.0.1 --port $Port"
    $res = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $cmd
        CurrentDirectory = $ProjectRoot
    }

    Write-Host "[LAUNCHER] Spawned web_server (PID: $($res.ProcessId)). Waiting for health endpoint..."
    $started = $false
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 500
        if (Test-BackendHealth) {
            $started = $true
            break
        }
    }
    if ($started) {
        Write-Host "[LAUNCHER] Backend web_server is ONLINE and healthy." -ForegroundColor Green
    } else {
        Write-Host "[LAUNCHER] ERROR: Backend failed to respond to $HealthUrl within 15 seconds." -ForegroundColor Red
    }
}

# 2. Verification Bot Discord (single-instance)
$discordRunning = $false
try {
    $procs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        if ($p.CommandLine -and $p.CommandLine -like "*discord_client*") {
            $discordRunning = $true
            Write-Host "[LAUNCHER] Discord bot is ALREADY running (PID: $($p.ProcessId)). Reusing existing instance." -ForegroundColor Green
            break
        }
    }
} catch {
    $discordRunning = $false
}

if (-not $discordRunning) {
    Write-Host "[LAUNCHER] Starting Discord bot..." -ForegroundColor Yellow
    $botCmd = "`"$PythonExe`" -m core.integrations.discord.discord_client"
    $botRes = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
        CommandLine = $botCmd
        CurrentDirectory = $ProjectRoot
    }

    Write-Host "[LAUNCHER] Spawned Discord bot (PID: $($botRes.ProcessId))." -ForegroundColor Green
}
