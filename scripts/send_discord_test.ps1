$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

param(
    [string]$Message = "E-ZZIO est vivant sur Discord.",
    [switch]$Send
)

$BaseUrl = "http://127.0.0.1:8000"

$body = @{
    content = $Message
    username = "E-ZZIO"
    allow_send = [bool]$Send
} | ConvertTo-Json -Depth 10

Invoke-RestMethod "$BaseUrl/omni/discord/webhook" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
