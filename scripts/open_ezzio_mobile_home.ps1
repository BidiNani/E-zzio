$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Start-Process "http://127.0.0.1:8001/supervisor/mobile-home"

