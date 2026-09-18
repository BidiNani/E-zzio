$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$BaseUrl = "http://127.0.0.1:8001"

Write-Host "=== E-ZZIO Mobile Bridge Test ===" -ForegroundColor Cyan

Invoke-RestMethod "$BaseUrl/omni-bridge/status" -Method GET
Invoke-RestMethod "$BaseUrl/omni-bridge/mobile/config" -Method GET

