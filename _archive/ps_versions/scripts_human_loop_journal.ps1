param(
    [int]$Limit = 12
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$res = Invoke-RestMethod "http://127.0.0.1:8001/human/journal?limit=$Limit" -Method GET -TimeoutSec 90

Write-Host "=== E-ZZIO HUMAN JOURNAL ===" -ForegroundColor Cyan
Write-Host "Journal : $($res.journal_path)"
Write-Host "Events  : $($res.count)"
Write-Host ""

$res.events | ForEach-Object {
    [pscustomobject]@{
        created_at = $_.created_at
        type = $_.type
        id = $_.id
        cpu_ram_only = $_.policy.cpu_ram_only
        safe_only = $_.policy.safe_only
    }
}

