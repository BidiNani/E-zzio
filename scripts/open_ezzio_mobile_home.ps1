$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Start-Process "http://127.0.0.1:8000/supervisor/mobile-home"
