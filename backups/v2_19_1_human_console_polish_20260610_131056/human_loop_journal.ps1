param(
    [int]$Limit = 20
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Invoke-RestMethod "http://127.0.0.1:8000/human/journal?limit=$Limit" -Method GET -TimeoutSec 90
