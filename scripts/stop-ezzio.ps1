<#
.SYNOPSIS
    E-zzio — Arrêt global.
.DESCRIPTION
    Tue toutes les instances backend (port 8001) et frontend (port 1420).
.EXAMPLE
    cd G:\AI\E-zzio
    .\stop-ezzio.ps1
#>
[CmdletBinding()]
param(
    [int]$Port     = 8001,
    [int]$VitePort = 1420
)

function OK($t)   { Write-Host "  OK   $t" -ForegroundColor Green }
function Warn($t) { Write-Host "  WARN $t" -ForegroundColor Yellow }

Write-Host ""
Write-Host "E-ZZIO — Arrêt" -ForegroundColor Cyan
Write-Host "─────────────" -ForegroundColor Cyan

function KillPort($port) {
    $netstat = netstat -ano -p TCP 2>$null
    $pids = @()
    foreach ($line in $netstat) {
        $p = ($line -split '\s+') | Where-Object { $_ -ne '' }
        if ($p.Count -ge 5 -and $p[0] -eq 'TCP' -and $p[3] -eq 'LISTENING' -and $p[1] -match ":$port$") {
            if ($p[4] -match '^\d+$') { $pids += [int]$p[4] }
        }
    }
    $pids = $pids | Sort-Object -Unique
    if ($pids.Count -eq 0) { Warn "Port $port déjà libre" }
    else {
        foreach ($pid_ in $pids) {
            try { Stop-Process -Id $pid_ -Force; OK "Port $port — PID $pid_ tué" } catch {}
        }
    }
}

KillPort $Port
KillPort $VitePort

Write-Host ""
Write-Host "E-ZZIO — Arrêté" -ForegroundColor Green
Write-Host ""