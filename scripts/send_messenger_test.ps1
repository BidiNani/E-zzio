$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

param(
    [string]$Message = "E-ZZIO est vivant sur Messenger.",
    [switch]$Send
)

$BaseUrl = "http://127.0.0.1:8001"

$body = @{
    text = $Message
    allow_send = [bool]$Send
} | ConvertTo-Json -Depth 10

Invoke-RestMethod "$BaseUrl/omni/messenger/send" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body

