$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$BaseUrl = "http://127.0.0.1:8000"

[pscustomobject]@{
    Status = Invoke-RestMethod "$BaseUrl/status" -Method GET
    Routers = Invoke-RestMethod "$BaseUrl/router-status" -Method GET
    Omni = Invoke-RestMethod "$BaseUrl/omni/status" -Method GET
    Bridge = Invoke-RestMethod "$BaseUrl/omni-bridge/status" -Method GET
    Commands = Invoke-RestMethod "$BaseUrl/omni-bridge/commands" -Method GET
    NoAds = Invoke-RestMethod "$BaseUrl/no-ads-policy" -Method GET
}
