$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

param(
    [int]$OlderThanDays = 14,
    [switch]$Apply
)

$ProjectRoot = "G:\AI\E-zzio"
$Targets = @(
    Join-Path $ProjectRoot "logs",
    Join-Path $ProjectRoot "state\snapshots"
)

$cutoff = (Get-Date).AddDays(-[math]::Abs($OlderThanDays))

Write-Host ""
Write-Host "=== E-ZZIO CLEANUP SAFE ===" -ForegroundColor Cyan
Write-Host "Mode Apply : $Apply"
Write-Host "Older than : $OlderThanDays days"
Write-Host "Cutoff     : $cutoff"
Write-Host ""

$files = @()

foreach ($target in $Targets) {
    if (Test-Path -LiteralPath $target) {
        $files += Get-ChildItem -LiteralPath $target -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object {
                $_.LastWriteTime -lt $cutoff -and
                $_.FullName -notmatch "\\backups\\"
            }
    }
}

$totalBytes = ($files | Measure-Object -Property Length -Sum).Sum
if ($null -eq $totalBytes) { $totalBytes = 0 }

$result = [pscustomobject]@{
    Apply = [bool]$Apply
    Count = $files.Count
    GB = [math]::Round($totalBytes / 1GB, 3)
    Cutoff = $cutoff
}

$result

if ($files.Count -gt 0) {
    $files | Select-Object FullName, @{Name="MB";Expression={[math]::Round($_.Length / 1MB, 2)}}, LastWriteTime |
        Sort-Object LastWriteTime |
        Format-Table -AutoSize
}

if ($Apply -and $files.Count -gt 0) {
    foreach ($file in $files) {
        Remove-Item -LiteralPath $file.FullName -Force -ErrorAction SilentlyContinue
    }
    Write-Host "✅ Nettoyage appliqué." -ForegroundColor Green
}
else {
    Write-Host "Dry-run seulement. Pour supprimer : cleanup_ezzio_safe.ps1 -Apply" -ForegroundColor Yellow
}
