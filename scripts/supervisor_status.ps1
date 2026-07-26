$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Invoke-RestMethod "http://127.0.0.1:8000/supervisor/status" -Method GET -TimeoutSec 60
