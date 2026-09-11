$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ============================================================
# E-ZZIO - STATUS COMFYUI CPU
# ============================================================

$ComfyUrl = "http://127.0.0.1:8188"
$Port = 8188

$connections = @(
    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" }
)

$processes = @()

foreach ($connection in $connections) {
    $ownerProcessId = [int]$connection.OwningProcess
    try {
        $process = Get-Process -Id $ownerProcessId -ErrorAction Stop
        $processes += [pscustomobject]@{
            PID = $ownerProcessId
            Name = $process.ProcessName
            Path = $process.Path
            StartTime = $process.StartTime
        }
    }
    catch {
        $processes += [pscustomobject]@{
            PID = $ownerProcessId
            Name = "unknown"
            Path = ""
            StartTime = $null
        }
    }
}

$health = $null
$online = $false

try {
    $health = Invoke-RestMethod "$ComfyUrl/system_stats" -Method GET -TimeoutSec 3
    $online = $true
}
catch {
    $health = @{
        error = $_.Exception.Message
    }
}

[pscustomobject]@{
    Online = $online
    Url = $ComfyUrl
    Port = $Port
    ProcessCount = $processes.Count
    Processes = $processes
    Health = $health
    Policy = "CPU/RAM only"
}
