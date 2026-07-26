$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-WebRequest "http://127.0.0.1:8000/ui" -Method GET -TimeoutSec 10

Write-Host "=== E-ZZIO UI STATUS ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = ($res.StatusCode -eq 200)
    status_code = $res.StatusCode
    length = $res.Content.Length
    url = "http://127.0.0.1:8000/ui"
}
