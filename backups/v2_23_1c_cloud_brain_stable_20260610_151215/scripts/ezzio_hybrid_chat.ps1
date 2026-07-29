param(
    [Parameter(Mandatory=$true)]
    [string]$Text,

    [string]$Provider = "auto",

    [switch]$ForceCloud
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
    text = $Text
    provider = $Provider
    force_cloud = [bool]$ForceCloud
} | ConvertTo-Json -Depth 20

$res = Invoke-RestMethod "http://127.0.0.1:8000/api/chat/hybrid" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 240 `
    -Body $body

[pscustomobject]@{
    ok = $res.ok
    mode = $res.mode
    provider = $res.provider
    model = $res.model
    cache_hit = $res.cache_hit
    elapsed_ms = $res.elapsed_ms
    reply = $res.reply
}
