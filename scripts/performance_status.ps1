$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Invoke-RestMethod "http://127.0.0.1:8000/performance/status" -Method GET -TimeoutSec 30
