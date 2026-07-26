$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$BaseUrl = "http://127.0.0.1:8000"

$routes = Invoke-RestMethod "$BaseUrl/ezzio/routes" -Method GET -TimeoutSec 30

Write-Host ""
Write-Host "=== E-ZZIO ROUTES AUDIT ===" -ForegroundColor Cyan
Write-Host "Count      : $($routes.count)"
Write-Host "Duplicates : $($routes.duplicates | ConvertTo-Json -Compress)"
Write-Host ""

$routes.routes |
    Select-Object path, methods, endpoint |
    Sort-Object path |
    Format-Table -AutoSize
