$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Invoke-RestMethod "http://127.0.0.1:8001/api/brain/status" -Method GET -TimeoutSec 60

