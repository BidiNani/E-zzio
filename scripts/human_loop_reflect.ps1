param(
    [string]$Note = "réflexion manuelle : garder E-ZZIO stable, humain, local-first et prudent"
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$body = @{
    note = $Note
} | ConvertTo-Json -Depth 10

$res = Invoke-RestMethod "http://127.0.0.1:8000/human/reflect" `
    -Method POST `
    -ContentType "application/json" `
    -TimeoutSec 90 `
    -Body $body

Write-Host "=== E-ZZIO HUMAN REFLECTION ===" -ForegroundColor Cyan
[pscustomobject]@{
    ok = $res.ok
    version = $res.version
    note = $res.note
    identity = $res.identity.name
    role = $res.identity.role
    recent_event_count = $res.recent_event_count
    reflection = $res.reflection
}
