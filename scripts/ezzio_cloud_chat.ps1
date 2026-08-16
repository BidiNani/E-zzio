param(
    [Parameter(Mandatory=$true)]
    [string]$Text,

    [string]$Provider = "auto",

    [switch]$NoCache
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
    text = $Text
    provider = $Provider
    system = ""
    use_cache = -not $NoCache
} | ConvertTo-Json -Depth 20

$res = Invoke-RestMethod "http://127.0.0.1:8001/api/chat/cloud" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 240 `
    -Body $body

[pscustomobject]@{
    ok = $res.ok
    provider = $res.provider
    model = $res.model
    cache_hit = $res.cache_hit
    elapsed_ms = $res.elapsed_ms
    reply = $res.reply
}

