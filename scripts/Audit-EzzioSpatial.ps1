[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RootPath = "G:\AI\E-zzio"
Set-Location $RootPath

$AuditDir = "$RootPath\runtime\cleanup_audit"
New-Item -ItemType Directory -Force -Path $AuditDir | Out-Null

$ExcludedDirs = @("\.venv", "\.git", "__pycache__", "\node_modules")

$Files = Get-ChildItem -Path $RootPath -Recurse -File | Where-Object {
    $path = $_.FullName
    $skip = $false
    foreach ($ex in $ExcludedDirs) {
        if ($path -match [regex]::Escape($ex)) { $skip = $true; break }
    }
    -not $skip
}

$TopFiles = $Files | Sort-Object Length -Descending | Select-Object -First 20 | ForEach-Object {
    [PSCustomObject]@{
        Path         = $_.FullName.Substring($RootPath.Length + 1)
        SizeMB       = [math]::Round($_.Length / 1MB, 2)
        LastModified = $_.LastWriteTime.ToUniversalTime().ToString("yyyy-MM-dd")
    }
}

$ByExtension = $Files | Group-Object Extension | ForEach-Object {
    [PSCustomObject]@{
        Extension = if ($_.Name) { $_.Name } else { "[sans extension]" }
        Count     = $_.Count
        TotalMB   = [math]::Round(($_.Group | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    }
} | Sort-Object TotalMB -Descending

$FolderSizes = @{}
foreach ($f in $Files) {
    $rel = $f.FullName.Substring($RootPath.Length + 1)
    $topDir = $rel.Split([System.IO.Path]::DirectorySeparatorChar)[0]
    if (-not $FolderSizes.ContainsKey($topDir)) { $FolderSizes[$topDir] = 0 }
    $FolderSizes[$topDir] += $f.Length
}

$FolderReport = @(
    foreach ($dir in $FolderSizes.Keys) {
        [PSCustomObject]@{
            Directory = $dir
            TotalMB   = [math]::Round($FolderSizes[$dir] / 1MB, 2)
        }
    }
) | Sort-Object TotalMB -Descending

$SpatialReport = [PSCustomObject]@{
    GeneratedAt     = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    TopFiles        = $TopFiles
    ByExtension     = $ByExtension
    FolderVolumetry = $FolderReport
}

$ReportPath = "$AuditDir\spatial_report.json"
$SpatialReport | ConvertTo-Json -Depth 5 | Set-Content $ReportPath -Encoding UTF8

Write-Host "`n=== TOP DOSSIERS PAR VOLUMÉTRIE ===" -ForegroundColor Cyan
$FolderReport | Select-Object -First 5 | Format-Table -AutoSize

Write-Host "`n=== TOP 5 DES PLUS GROS FICHIERS ===" -ForegroundColor Cyan
$TopFiles | Select-Object -First 5 | Format-Table -AutoSize

Write-Host "`n=== TOP 5 EXTENSIONS DOMINANTES ===" -ForegroundColor Cyan
$ByExtension | Select-Object -First 5 | Format-Table -AutoSize
