param(
    [switch]$Quiet
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$PidPath = Join-Path $ProjectRoot "state\svelte_ui.pid"

if (-not $Quiet) {
    Write-Host "=== E-ZZIO STOP SVELTE UI ===" -ForegroundColor Cyan
}

$stopped = @()

if (Test-Path -LiteralPath $PidPath) {
    try {
        $savedPid = [int](Get-Content -LiteralPath $PidPath -Raw)
        $p = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
        if ($p) {
            Stop-Process -Id $savedPid -Force
            $stopped += $savedPid
        }
    } catch {}
}

Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    ForEach-Object {
        $ownerProcessId = [int]$_.OwningProcess
        try {
            Stop-Process -Id $ownerProcessId -Force
            $stopped += $ownerProcessId
        } catch {}
    }

Start-Sleep -Seconds 1

if (-not $Quiet) {
    [pscustomobject]@{
        stopped_count = $stopped.Count
        stopped_pids = ($stopped -join ", ")
        frontend_url = "http://127.0.0.1:5173"
    }
}
