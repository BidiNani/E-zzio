$ErrorActionPreference = "SilentlyContinue"

$Port = 8000

Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    ForEach-Object {
        $ownerProcessId = [int]$_.OwningProcess
        Stop-Process -Id $ownerProcessId -Force
        Write-Host "E-ZZIO stoppé : PID=$ownerProcessId"
    }
