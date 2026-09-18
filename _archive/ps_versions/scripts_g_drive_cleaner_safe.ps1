param(
    [string]$DriveRoot = "G:\",
    [switch]$Apply,
    [switch]$Quarantine,
    [int]$OldDays = 14,
    [int]$LargeFileGB = 2
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ProjectRoot = "G:\AI\E-zzio"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$ReportRoot = Join-Path $ProjectRoot "reports\g_drive_cleaner_$Stamp"
$QuarantineRoot = Join-Path $ProjectRoot "quarantine\g_drive_cleaner_$Stamp"

New-Item -ItemType Directory -Force -Path $ReportRoot | Out-Null
if ($Quarantine) {
    New-Item -ItemType Directory -Force -Path $QuarantineRoot | Out-Null
}

$env:OLLAMA_NUM_GPU = "0"
$env:CUDA_VISIBLE_DEVICES = ""
$env:GGML_CUDA = "0"
$env:CUDA_DEVICE_ORDER = "PCI_BUS_ID"
$env:EZZIO_GPU_POLICY = "cpu_ram_only"
$env:EZZIO_NUM_GPU = "0"
$env:EZZIO_NO_ADS = "true"
$env:EZZIO_NO_TRACKING = "true"
$env:EZZIO_NO_SPONSORS = "true"

$ProtectedFragments = @(
    "\AI\E-zzio\secrets\",
    "\AI\E-zzio\state\",
    "\AI\external\ComfyUI\models\",
    "\AI\external\ComfyUI\output\",
    "\ollama\",
    "\models\",
    "\checkpoints\",
    "\loras\",
    "\vae\",
    "\embeddings\",
    "\SteamLibrary\",
    "\Battle.net\",
    "\Games\",
    "\Saved Games\"
)

$ProtectedExtensions = @(
    ".safetensors", ".ckpt", ".pt", ".pth", ".onnx", ".gguf", ".bin",
    ".sqlite", ".db", ".env", ".key", ".pem", ".jsonl"
)

$SafeDirNames = @(
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".svelte-kit",
    ".vite",
    ".cache"
)

$SafeFileExtensions = @(
    ".tmp", ".temp", ".log", ".dmp", ".dump", ".trace"
)

function Normalize-PathText {
    param([string]$Path)
    return ($Path -replace "/", "\")
}

function Test-ProtectedPath {
    param([string]$Path)

    $p = (Normalize-PathText $Path).ToLowerInvariant()

    foreach ($frag in $ProtectedFragments) {
        if ($p.Contains($frag.ToLowerInvariant())) {
            return $true
        }
    }

    return $false
}

function Format-Size {
    param([double]$Bytes)

    if ($Bytes -ge 1TB) { return "{0:N2} TB" -f ($Bytes / 1TB) }
    if ($Bytes -ge 1GB) { return "{0:N2} GB" -f ($Bytes / 1GB) }
    if ($Bytes -ge 1MB) { return "{0:N2} MB" -f ($Bytes / 1MB) }
    if ($Bytes -ge 1KB) { return "{0:N2} KB" -f ($Bytes / 1KB) }
    return "$Bytes B"
}

function Get-DirectorySize {
    param([string]$Path)

    $sum = 0L
    try {
        Get-ChildItem -LiteralPath $Path -Recurse -Force -File -ErrorAction SilentlyContinue |
            ForEach-Object { $sum += $_.Length }
    } catch {}

    return $sum
}

function Move-ToQuarantine {
    param([string]$Path)

    $relative = $Path.Substring($DriveRoot.Length).TrimStart("\")
    $target = Join-Path $QuarantineRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Move-Item -LiteralPath $Path -Destination $target -Force
    return $target
}

Write-Host ""
Write-Host "=== E-ZZIO G DRIVE CLEANER SAFE v2.27.1 ===" -ForegroundColor Cyan
Write-Host "Drive      : $DriveRoot"
Write-Host "Apply      : $Apply"
Write-Host "Quarantine : $Quarantine"
Write-Host "Reports    : $ReportRoot"
Write-Host ""

if (-not (Test-Path -LiteralPath $DriveRoot)) {
    throw "Drive introuvable : $DriveRoot"
}

$ActionsPath = Join-Path $ReportRoot "actions.jsonl"
$SafeCandidatesPath = Join-Path $ReportRoot "safe_candidates.json"
$LargeFilesPath = Join-Path $ReportRoot "large_files_review.json"
$SummaryPath = Join-Path $ReportRoot "summary.json"

$safeCandidates = New-Object System.Collections.Generic.List[object]
$largeFiles = New-Object System.Collections.Generic.List[object]

Write-Host "[1/5] Scan dossiers cache/temp sûrs..." -ForegroundColor Yellow

Get-ChildItem -LiteralPath $DriveRoot -Recurse -Force -Directory -ErrorAction SilentlyContinue |
    Where-Object {
        ($SafeDirNames -contains $_.Name) -and
        (-not (Test-ProtectedPath $_.FullName))
    } |
    ForEach-Object {
        $size = Get-DirectorySize $_.FullName
        $safeCandidates.Add([pscustomobject]@{
            type = "directory"
            path = $_.FullName
            size_bytes = $size
            size = Format-Size $size
            reason = "safe_cache_directory"
            last_write = $_.LastWriteTime.ToString("s")
        })
    }

Write-Host "[2/5] Scan fichiers temporaires/logs anciens..." -ForegroundColor Yellow

$limitDate = (Get-Date).AddDays(-$OldDays)

Get-ChildItem -LiteralPath $DriveRoot -Recurse -Force -File -ErrorAction SilentlyContinue |
    ForEach-Object {
        $file = $_
        $ext = $file.Extension.ToLowerInvariant()

        if (Test-ProtectedPath $file.FullName) { return }
        if ($ProtectedExtensions -contains $ext) { return }

        if (($SafeFileExtensions -contains $ext) -and ($file.LastWriteTime -lt $limitDate)) {
            $safeCandidates.Add([pscustomobject]@{
                type = "file"
                path = $file.FullName
                size_bytes = $file.Length
                size = Format-Size $file.Length
                reason = "old_temp_log_file"
                last_write = $file.LastWriteTime.ToString("s")
            })
        }

        if ($file.Length -ge ($LargeFileGB * 1GB)) {
            $largeFiles.Add([pscustomobject]@{
                path = $file.FullName
                size_bytes = $file.Length
                size = Format-Size $file.Length
                extension = $file.Extension
                protected = ($ProtectedExtensions -contains $ext) -or (Test-ProtectedPath $file.FullName)
                last_write = $file.LastWriteTime.ToString("s")
            })
        }
    }

Write-Host "[3/5] Rapports..." -ForegroundColor Yellow

$safeCandidates |
    Sort-Object size_bytes -Descending |
    ConvertTo-Json -Depth 40 |
    Set-Content -LiteralPath $SafeCandidatesPath -Encoding UTF8

$largeFiles |
    Sort-Object size_bytes -Descending |
    ConvertTo-Json -Depth 40 |
    Set-Content -LiteralPath $LargeFilesPath -Encoding UTF8

Write-Host "[4/5] Nettoyage..." -ForegroundColor Yellow

$wouldFree = 0L
$freed = 0L
$deletedCount = 0
$quarantinedCount = 0
$failedCount = 0

foreach ($item in $safeCandidates) {
    $wouldFree += [int64]$item.size_bytes

    if (-not (Test-Path -LiteralPath $item.path)) {
        continue
    }

    $event = [ordered]@{
        created_at = (Get-Date).ToString("s")
        path = $item.path
        type = $item.type
        size_bytes = $item.size_bytes
        size = $item.size
        reason = $item.reason
    }

    try {
        if (-not $Apply) {
            $event.action = "dry_run_would_remove"
        }
        elseif ($Quarantine) {
            $target = Move-ToQuarantine $item.path
            $event.action = "quarantined"
            $event.target = $target
            $freed += [int64]$item.size_bytes
            $quarantinedCount++
        }
        else {
            Remove-Item -LiteralPath $item.path -Recurse -Force -ErrorAction Stop
            $event.action = "deleted"
            $freed += [int64]$item.size_bytes
            $deletedCount++
        }
    }
    catch {
        $event.action = "failed"
        $event.error = $_.Exception.Message
        $failedCount++
    }

    ($event | ConvertTo-Json -Depth 20 -Compress) |
        Add-Content -LiteralPath $ActionsPath -Encoding UTF8
}

Write-Host "[5/5] Résumé..." -ForegroundColor Yellow

$summary = [ordered]@{
    created_at = (Get-Date).ToString("s")
    version = "v2.27.1-g-drive-cleaner-safe"
    drive = $DriveRoot
    mode = if ($Apply) { if ($Quarantine) { "apply_quarantine" } else { "apply_delete" } } else { "dry_run" }
    safe_candidates_count = $safeCandidates.Count
    safe_reclaim_possible_bytes = $wouldFree
    safe_reclaim_possible = Format-Size $wouldFree
    deleted_count = $deletedCount
    quarantined_count = $quarantinedCount
    freed_bytes = $freed
    freed = Format-Size $freed
    failed_count = $failedCount
    large_files_review_count = $largeFiles.Count
    reports = @{
        summary = $SummaryPath
        safe_candidates = $SafeCandidatesPath
        large_files_review = $LargeFilesPath
        actions = $ActionsPath
    }
    quarantine_root = if ($Quarantine) { $QuarantineRoot } else { $null }
    protections = @{
        ai_models = $true
        comfy_models = $true
        ollama = $true
        secrets = $true
        state = $true
        saves = $true
        games = $true
    }
    gpu_policy = "cpu_ram_only"
    no_ads = $true
}

$summary | ConvertTo-Json -Depth 80 |
    Set-Content -LiteralPath $SummaryPath -Encoding UTF8

Write-Host ""
Write-Host "=== RÉSUMÉ ===" -ForegroundColor Cyan
[pscustomobject]@{
    mode = $summary.mode
    safe_candidates = $summary.safe_candidates_count
    reclaim_possible = $summary.safe_reclaim_possible
    deleted = $summary.deleted_count
    quarantined = $summary.quarantined_count
    freed = $summary.freed
    failed = $summary.failed_count
    large_files_to_review = $summary.large_files_review_count
    report = $SummaryPath
}

Write-Host ""
Write-Host "Rapports :" -ForegroundColor Cyan
Write-Host "Résumé          : $SummaryPath"
Write-Host "Candidats sûrs  : $SafeCandidatesPath"
Write-Host "Gros fichiers   : $LargeFilesPath"
Write-Host "Actions         : $ActionsPath"

if (-not $Apply) {
    Write-Host ""
    Write-Host "Mode DRY RUN : rien n'a été supprimé." -ForegroundColor Yellow
    Write-Host "Étape conseillée :" -ForegroundColor Yellow
    Write-Host "G:\AI\E-zzio\scripts\g_drive_cleaner_safe.ps1 -Apply -Quarantine"
}
