<# E-ZZIO - Stack Discord : backend :8001 + bot premier plan. ASCII only (PS5.1). #>
$ErrorActionPreference = "Stop"
$Root = "G:/AI/E-zzio"
$Py = "$Root/.venv/Scripts/python.exe"

function Test-Port8001 {
    try {
        $c = New-Object Net.Sockets.TcpClient
        $r = $c.BeginConnect("127.0.0.1", 8001, $null, $null)
        $ok = $r.AsyncWaitHandle.WaitOne(800)
        $c.Close()
        return $ok
    } catch { return $false }
}

function Test-Health8001 {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8001/health" -TimeoutSec 4 -UseBasicParsing
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

function Stop-Orphan8001 {
    try {
        $conn = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -eq $conn) { return }
        $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
        if ($null -eq $proc) { return }
        if ($proc.ProcessName -like "*python*") {
            Stop-Process -Id $proc.Id -Force
            Start-Sleep -Seconds 2
            "[STACK] Orphan $($proc.Id) killed."
        } else {
            "[STACK] Port held by non-python PID $($proc.Id) ($($proc.ProcessName)) : left alone."
        }
    } catch { "[STACK] Orphan check skipped : $($_.Exception.Message)" }
}

if (-not (Test-Health8001)) {
    if (Test-Port8001) { Stop-Orphan8001 }
    if (-not (Test-Health8001)) {
        "[STACK] Backend down - starting uvicorn..."
        Start-Job -Name "ezzio-backend" -ScriptBlock {
            Set-Location $using:Root
            & $using:Py -m uvicorn web_server:app --host 127.0.0.1 --port 8001
        } | Out-Null
    }
    $deadline = (Get-Date).AddSeconds(15)
    while (-not (Test-Health8001) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 500 }
    if (-not (Test-Health8001)) {
        "[STACK] FAIL : backend :8001 unhealthy after 15 s."
        exit 1
    }
}
"[STACK] Backend :8001 healthy - starting Discord bot (foreground)..."
& $Py "$Root/core/integrations/discord/discord_client.py"
