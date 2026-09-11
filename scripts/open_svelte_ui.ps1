$ErrorActionPreference = "Stop"

try {
    Invoke-WebRequest "http://127.0.0.1:5173" -Method GET -TimeoutSec 5 | Out-Null
} catch {
    & "G:\AI\E-zzio\scripts\start_svelte_ui.ps1"
    return
}

Start-Process "http://127.0.0.1:5173"
