[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RootPath = "G:\AI\E-zzio"
Set-Location $RootPath

$AuditDir = "$RootPath\runtime\cleanup_audit"
New-Item -ItemType Directory -Force -Path $AuditDir | Out-Null

$ExcludedDirs = @("\.venv", "\.git", "__pycache__", "\node_modules", "\ezzio-ui")

$Files = Get-ChildItem -Path $RootPath -Recurse -File | Where-Object {
    $path = $_.FullName
    $skip = $false
    foreach ($ex in $ExcludedDirs) {
        if ($path -match [regex]::Escape($ex)) { $skip = $true; break }
    }
    -not $skip -and ($_.Extension -in @(".py", ".ps1", ".json", ".md"))
}

$FileCorpus = @{}
foreach ($f in $Files) {
    $relPath = $f.FullName.Substring($RootPath.Length + 1)
    try {
        $FileCorpus[$relPath] = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
    } catch {
        $FileCorpus[$relPath] = ""
    }
}

$KnownEntrypoints = @(
    "web_server.py",
    "core\runtime\advanced_watchdog.py",
    "core\runtime\log_rotator.py",
    "runtime\launcher\start_ezzio_api.ps1",
    "scripts\Certify-EzzioReadOnly-v2.1.ps1",
    "scripts\Audit-EzzioStorage.ps1",
    "scripts\Setup-EzzioRecovery.ps1",
    "scripts\Audit-EzzioOrphans.ps1"
)

$ClassificationReport = @()

foreach ($path in $FileCorpus.Keys) {
    $fileName = [System.IO.Path]::GetFileName($path)
    $ext = [System.IO.Path]::GetExtension($path)
    $content = $FileCorpus[$path]

    $status = "UNKNOWN"
    $reason = ""

    if ($path -match "runtime[\\/]state|runtime[\\/]logs|runtime[\\/]cleanup_audit|audit[\\/]") {
        $status = "GENERATED"
        $reason = "Located in runtime state, logs or audit trace directory"
    }
    elseif ($KnownEntrypoints -contains $path -or $path -match "start_ezzio_api\.ps1$") {
        $status = "ACTIVE"
        $reason = "Known sovereign runtime entrypoint or active script"
    }
    else {
        $isReferenced = $false
        foreach ($otherPath in $FileCorpus.Keys) {
            if ($otherPath -eq $path) { continue }
            $otherContent = $FileCorpus[$otherPath]
            $baseNameNoExt = [System.IO.Path]::GetFileNameWithoutExtension($path)
            if ($otherContent -match [regex]::Escape($fileName) -or ($ext -eq ".py" -and $otherContent -match [regex]::Escape($baseNameNoExt))) {
                $isReferenced = $true
                break
            }
        }

        if ($isReferenced) {
            $status = "REFERENCED"
            $reason = "Cited or imported by at least one other component"
        }
        elseif ($path -match "archive|old|backup|_v\d+") {
            $status = "HISTORICAL"
            $reason = "Contains archival or version naming pattern"
        }
        else {
            $status = "ORPHAN_CANDIDATE"
            $reason = "Zero inbound references detected and not a known entrypoint"
        }
    }

    $fileInfo = Get-Item "$RootPath\$path" -ErrorAction SilentlyContinue
    $size = if ($fileInfo) { $fileInfo.Length } else { 0 }
    $lastMod = if ($fileInfo) { $fileInfo.LastWriteTime.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ") } else { "UNKNOWN" }

    $ClassificationReport += [PSCustomObject]@{
        Path         = $path
        Status       = $status
        Reason       = $reason
        Size         = $size
        LastModified = $lastMod
    }
}

$ReportPath = "$AuditDir\orphan_classification.json"
$ClassificationReport | ConvertTo-Json -Depth 5 | Set-Content $ReportPath -Encoding UTF8

$Summary = $ClassificationReport | Group-Object Status | Select-Object Name, Count
Write-Host "`n=== SYNTHÈSE DE CLASSIFICATION ORPHELINS ===" -ForegroundColor Cyan
$Summary | Format-Table -AutoSize
