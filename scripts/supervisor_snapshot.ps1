$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Invoke-RestMethod "http://127.0.0.1:8000/supervisor/snapshot" -Method POST -TimeoutSec 60
Invoke-RestMethod "http://127.0.0.1:8000/supervisor/snapshots" -Method GET -TimeoutSec 30
