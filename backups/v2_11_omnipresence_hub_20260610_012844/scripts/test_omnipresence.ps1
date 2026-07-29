$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$BaseUrl = "http://127.0.0.1:8000"

Write-Host "=== E-ZZIO Omnipresence Test ===" -ForegroundColor Cyan

Invoke-RestMethod "$BaseUrl/omni/status" -Method GET

Invoke-RestMethod "$BaseUrl/omni/inbox" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"source":"powershell","user":"enrik","text":"Test inbox local E-ZZIO omnipresence","metadata":{"mode":"test"}}'

Invoke-RestMethod "$BaseUrl/omni/mobile/push" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"title":"E-ZZIO","text":"Message local prêt pour smartphone.","channel":"local"}'

Invoke-RestMethod "$BaseUrl/omni/mobile/pull?limit=5" -Method GET

Invoke-RestMethod "$BaseUrl/omni/discord/webhook" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"content":"E-ZZIO test Discord dry-run depuis PowerShell.","username":"E-ZZIO","allow_send":false}'

Invoke-RestMethod "$BaseUrl/omni/messenger/send" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"text":"E-ZZIO test Messenger dry-run depuis PowerShell.","allow_send":false}'
