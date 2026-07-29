$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$ApiUrl = "http://127.0.0.1:8000"
$ComfyUrl = "http://127.0.0.1:8188"

function Test-Url {
    param(
        [string]$Url,
        [int]$TimeoutSec = 3
    )

    try {
        $res = Invoke-RestMethod $Url -Method GET -TimeoutSec $TimeoutSec
        return [pscustomobject]@{
            Ok = $true
            Url = $Url
            Data = $res
            Error = $null
        }
    }
    catch {
        return [pscustomobject]@{
            Ok = $false
            Url = $Url
            Data = $null
            Error = $_.Exception.Message
        }
    }
}

function Get-PortProcesses {
    param([int]$Port)

    $items = @()

    Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Listen" } |
        ForEach-Object {
            $ownerProcessId = [int]$_.OwningProcess
            try {
                $p = Get-Process -Id $ownerProcessId -ErrorAction Stop
                $items += [pscustomobject]@{
                    Port = $Port
                    PID = $ownerProcessId
                    Name = $p.ProcessName
                    Path = $p.Path
                    StartTime = $p.StartTime
                }
            }
            catch {
                $items += [pscustomobject]@{
                    Port = $Port
                    PID = $ownerProcessId
                    Name = "unknown"
                    Path = ""
                    StartTime = $null
                }
            }
        }

    return @($items)
}

$ApiStatus = Test-Url "$ApiUrl/status"
$RouterStatus = Test-Url "$ApiUrl/router-status"
$SupervisorStatus = Test-Url "$ApiUrl/supervisor/status" 10
$Watchdog = Test-Url "$ApiUrl/supervisor/watchdog" 15
$ComfyStatus = Test-Url "$ComfyUrl/system_stats"

[pscustomobject]@{
    CreatedAt = (Get-Date).ToString("s")
    ProjectRoot = $ProjectRoot
    ApiOnline = $ApiStatus.Ok
    RouterOnline = $RouterStatus.Ok
    SupervisorOnline = $SupervisorStatus.Ok
    WatchdogOk = if ($Watchdog.Ok) { $Watchdog.Data.ok } else { $false }
    ComfyOnline = $ComfyStatus.Ok
    ApiProcesses = @(Get-PortProcesses 8000)
    ComfyProcesses = @(Get-PortProcesses 8188)
    ApiStatus = $ApiStatus.Data
    RouterStatus = $RouterStatus.Data
    Watchdog = $Watchdog.Data
    Policy = @{
        CPU_RAM_ONLY = $true
        GPU = "untouched"
        NO_ADS = $true
        NO_TRACKING = $true
        NO_SPONSORS = $true
    }
}
