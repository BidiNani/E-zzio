$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8001/supervisor/watchdog" -Method GET -TimeoutSec 90

$res.actions
$res

