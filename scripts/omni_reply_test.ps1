$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

param(
    [string]$Text = "Salut E-ZZIO, réponds comme si j'étais sur mon smartphone."
)

$BaseUrl = "http://127.0.0.1:8001"

$body = @{
    text = $Text
    source = "powershell"
    user = "enrik"
    mode = "fast"
} | ConvertTo-Json -Depth 20

Invoke-RestMethod "$BaseUrl/omni-bridge/reply" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 180 `
    -Body $body

