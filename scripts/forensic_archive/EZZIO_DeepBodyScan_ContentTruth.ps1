#Requires -Version 7.0
<#
.SYNOPSIS
    E-ZZIO — Deep Body Scan / Content Truth Engine
    Scan profond READ-ONLY d'un dossier : pour chaque fichier, lecture single-pass
    (hash SHA-256 calculé pendant la lecture, aucune double passe), enregistrement
    forensic chaîné (records.jsonl + checkpoint.json avec chaîne de hash), reprise
    certifiée après interruption, et quality gates fail-closed avant certification.

.DESCRIPTION
    Ce script NE MODIFIE JAMAIS le dossier scanné (RootPath). Toute écriture se fait
    exclusivement dans un workspace transactionnel isolé sous OutputRoot.

    Pipeline :
      1. Découverte déterministe des fichiers (triés par chemin complet)
      2. Reprise éventuelle depuis un checkpoint existant (--ResumeRunId)
      3. Lecture single-pass de chaque fichier (stream, hash calculé en marchant)
      4. Écriture d'un record JSONL par fichier + chaînage (ChainHash = SHA256(prev + record))
      5. Checkpoint périodique (atomique : écrit dans un temp, puis renommé)
      6. Quality gates finales (fail-closed : au moindre doute, PAS de certification)
      7. Commit atomique du run en zone "final" seulement si TOUTES les gates passent

.PARAMETER RootPath
    Dossier à scanner (le "corps" d'E-zzio). Jamais modifié.

.PARAMETER OutputRoot
    Dossier de sortie forensic. DOIT être en dehors de RootPath (vérifié au démarrage).

.PARAMETER ResumeRunId
    RunId d'un scan précédent interrompu, pour reprendre au lieu de recommencer.

.PARAMETER ExcludeDirs
    Noms de dossiers à exclure complètement de la découverte (protection secrets, .git, etc.)

.PARAMETER CheckpointEveryNFiles
    Fréquence d'écriture du checkpoint (par défaut toutes les 250 fichiers).

.PARAMETER ChunkSizeBytes
    Taille de bloc de lecture en streaming (par défaut 1 Mo).

.EXAMPLE
    .\EZZIO_DeepBodyScan_ContentTruth.ps1 -RootPath "G:\AI\E-zzio" -OutputRoot "G:\AI\_forensic\ContentTruth"

.EXAMPLE
    # Reprendre un run interrompu
    .\EZZIO_DeepBodyScan_ContentTruth.ps1 -RootPath "G:\AI\E-zzio" -OutputRoot "G:\AI\_forensic\ContentTruth" -ResumeRunId "20260820_143200_001"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RootPath,

    [Parameter(Mandatory = $true)]
    [string]$OutputRoot,

    [string]$ResumeRunId = $null,

    [string[]]$ExcludeDirs = @(
        '.git', '.ssh', 'secrets', 'private_keys', 'node_modules',
        '__pycache__', '.venv', 'venv', '_archive', '_archive_memoire_morte',
        '_a_verifier', '_backups_auto', 'archive', 'backups', 'quarantine',
        'runtime\guardian', '.transaction_2b'
    ),

    [int]$CheckpointEveryNFiles = 250,

    [int]$ChunkSizeBytes = 1MB
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================
# 0. GARDE-FOUS DE DÉPART (FAIL-CLOSED)
# ============================================================

function Write-Phase {
    param([string]$Text)
    Write-Host ""
    Write-Host "=== $Text ===" -ForegroundColor Cyan
}

function Get-CanonicalPath {
    param([string]$Path)
    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
}

$RootPathCanon   = Get-CanonicalPath $RootPath
$OutputRootCanon = Get-CanonicalPath $OutputRoot

if (-not (Test-Path -LiteralPath $RootPathCanon -PathType Container)) {
    throw "FAIL-CLOSED: RootPath introuvable ou n'est pas un dossier : $RootPathCanon"
}

# Le dossier de sortie ne doit JAMAIS être à l'intérieur du dossier scanné,
# sinon le scan pollue son propre corpus et fausse la vérité observée.
if ($OutputRootCanon.StartsWith($RootPathCanon, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "FAIL-CLOSED: OutputRoot ($OutputRootCanon) ne doit pas être situé sous RootPath ($RootPathCanon)."
}

if (-not (Test-Path -LiteralPath $OutputRootCanon)) {
    New-Item -ItemType Directory -Path $OutputRootCanon -Force | Out-Null
}

# ============================================================
# 1. INITIALISATION DU RUN (nouveau ou reprise)
# ============================================================

Write-Phase "INITIALISATION"

$isResume = [bool]$ResumeRunId

if ($isResume) {
    $RunId = $ResumeRunId
    $TransactionRoot = Join-Path $OutputRootCanon ".transaction_$RunId"
    if (-not (Test-Path -LiteralPath $TransactionRoot)) {
        throw "FAIL-CLOSED: ResumeRunId '$RunId' fourni mais aucun workspace transactionnel trouvé à $TransactionRoot"
    }
    Write-Host "Reprise du run : $RunId" -ForegroundColor Yellow
}
else {
    $RunId = (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + (Get-Random -Minimum 100 -Maximum 999)
    $TransactionRoot = Join-Path $OutputRootCanon ".transaction_$RunId"
    New-Item -ItemType Directory -Path $TransactionRoot -Force | Out-Null
    Write-Host "Nouveau run : $RunId" -ForegroundColor Green
}

$StagingDir     = Join-Path $TransactionRoot 'staging'
$FinalDir       = Join-Path $OutputRootCanon "run_$RunId"
$RecordsPath    = Join-Path $StagingDir 'records.jsonl'
$CheckpointPath = Join-Path $StagingDir 'checkpoint.json'
$GatesPath      = Join-Path $StagingDir 'quality_gates.json'
$ManifestPath   = Join-Path $StagingDir 'run_manifest.json'

New-Item -ItemType Directory -Path $StagingDir -Force | Out-Null

# ============================================================
# 2. DÉCOUVERTE DÉTERMINISTE DES FICHIERS
# ============================================================

Write-Phase "DÉCOUVERTE DES FICHIERS"

function Test-PathExcluded {
    param([string]$FullPath, [string]$RootPath, [string[]]$ExcludeDirs)
    $relative = $FullPath.Substring($RootPath.Length).TrimStart('\', '/')
    foreach ($ex in $ExcludeDirs) {
        $exNorm = $ex.Replace('/', '\')
        if ($relative -like "*$exNorm*") { return $true }
    }
    return $false
}

Write-Host "Énumération récursive de $RootPathCanon ..."
$allFiles = Get-ChildItem -LiteralPath $RootPathCanon -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object { -not (Test-PathExcluded -FullPath $_.FullName -RootPath $RootPathCanon -ExcludeDirs $ExcludeDirs) } |
    Sort-Object -Property FullName

$totalFiles = $allFiles.Count
Write-Host "Fichiers découverts (hors exclusions) : $totalFiles"

if ($totalFiles -eq 0) {
    throw "FAIL-CLOSED: aucun fichier découvert sous $RootPathCanon — vérifier RootPath/ExcludeDirs avant de continuer."
}

# ============================================================
# 3. CHARGEMENT DE L'ÉTAT DE REPRISE
# ============================================================

$processedPaths = [System.Collections.Generic.HashSet[string]]::new()
$lastChainHash  = ''
$filesProcessedCount = 0

if ($isResume -and (Test-Path -LiteralPath $CheckpointPath)) {
    Write-Phase "VÉRIFICATION DE L'ÉTAT DE REPRISE"

    $checkpoint = Get-Content -LiteralPath $CheckpointPath -Raw | ConvertFrom-Json

    if (-not (Test-Path -LiteralPath $RecordsPath)) {
        throw "FAIL-CLOSED: checkpoint.json présent mais records.jsonl absent — état incohérent, reprise refusée."
    }

    # Recalcul intégral de la chaîne à partir de records.jsonl pour vérifier
    # qu'elle correspond exactement à ce que le checkpoint prétend.
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $recomputedChain = ''
    $lineCount = 0

    foreach ($line in [System.IO.File]::ReadLines($RecordsPath)) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $record = $line | ConvertFrom-Json
        $processedPaths.Add($record.RelativePath) | Out-Null
        $toHash = "$recomputedChain|$($record.RecordHash)"
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($toHash)
        $hashBytes = $sha256.ComputeHash($bytes)
        $recomputedChain = [System.BitConverter]::ToString($hashBytes).Replace('-', '').ToLowerInvariant()
        $lineCount++
    }
    $sha256.Dispose()

    if ($recomputedChain -ne $checkpoint.ChainHash) {
        throw "FAIL-CLOSED: la chaîne recalculée depuis records.jsonl ($recomputedChain) ne correspond PAS au checkpoint ($($checkpoint.ChainHash)). Intégrité compromise — reprise refusée."
    }

    if ($lineCount -ne $checkpoint.FilesProcessed) {
        throw "FAIL-CLOSED: nombre de records ($lineCount) != FilesProcessed du checkpoint ($($checkpoint.FilesProcessed)). Reprise refusée."
    }

    $lastChainHash = $recomputedChain
    $filesProcessedCount = $lineCount
    Write-Host "Reprise validée : $filesProcessedCount fichiers déjà traités, chaîne intègre." -ForegroundColor Green
}
elseif (-not $isResume) {
    # Nouveau run : fichiers de staging vides mais créés pour écriture en streaming
    New-Item -ItemType File -Path $RecordsPath -Force | Out-Null
}

# ============================================================
# 4. SCAN SINGLE-PASS
# ============================================================

Write-Phase "SCAN SINGLE-PASS ($($totalFiles - $processedPaths.Count) fichiers restants)"

$recordsWriter = [System.IO.StreamWriter]::new($RecordsPath, $true, [System.Text.Encoding]::UTF8)
$errorCount = 0
$sha256Main = [System.Security.Cryptography.SHA256]::Create()

function Write-CheckpointAtomic {
    param([string]$Path, [hashtable]$Data)
    $tempPath = "$Path.tmp"
    ($Data | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $tempPath -Encoding UTF8
    Move-Item -LiteralPath $tempPath -Destination $Path -Force
}

$sinceLastCheckpoint = 0
$startTime = Get-Date

for ($i = 0; $i -lt $totalFiles; $i++) {
    $fileInfo = $allFiles[$i]
    $relativePath = $fileInfo.FullName.Substring($RootPathCanon.Length).TrimStart('\', '/')

    if ($processedPaths.Contains($relativePath)) {
        continue  # déjà traité lors d'un run précédent (reprise)
    }

    $record = [ordered]@{
        RelativePath  = $relativePath
        SizeExpected  = $fileInfo.Length
        BytesRead     = 0
        Hash          = $null
        RecordHash    = $null
        ObservedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
        Status        = 'PENDING'
        Error         = $null
        NativeAttrs   = $fileInfo.Attributes.ToString()
    }

    try {
        $stream = [System.IO.File]::Open($fileInfo.FullName, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
        try {
            $sha = [System.Security.Cryptography.SHA256]::Create()
            $buffer = New-Object byte[] $ChunkSizeBytes
            $bytesReadTotal = 0
            while (($bytesRead = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                $sha.TransformBlock($buffer, 0, $bytesRead, $null, 0) | Out-Null
                $bytesReadTotal += $bytesRead
            }
            $sha.TransformFinalBlock([byte[]]::new(0), 0, 0) | Out-Null
            $hashHex = [System.BitConverter]::ToString($sha.Hash).Replace('-', '').ToLowerInvariant()
            $sha.Dispose()

            $record.BytesRead = $bytesReadTotal
            $record.Hash = $hashHex
            $record.Status = if ($bytesReadTotal -eq $fileInfo.Length) { 'OBSERVED' } else { 'SIZE_MISMATCH' }
        }
        finally {
            $stream.Dispose()
        }
    }
    catch {
        $errorCount++
        $record.Status = 'ERROR'
        $record.Error = $_.Exception.Message
    }

    # RecordHash = empreinte du record lui-même (hors ChainHash), pour chaînage
    $recordForHash = $record | ConvertTo-Json -Compress
    $recordHashBytes = $sha256Main.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($recordForHash))
    $record.RecordHash = [System.BitConverter]::ToString($recordHashBytes).Replace('-', '').ToLowerInvariant()

    $chainInput = "$lastChainHash|$($record.RecordHash)"
    $chainHashBytes = $sha256Main.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($chainInput))
    $lastChainHash = [System.BitConverter]::ToString($chainHashBytes).Replace('-', '').ToLowerInvariant()

    $recordsWriter.WriteLine(($record | ConvertTo-Json -Compress))
    $filesProcessedCount++
    $sinceLastCheckpoint++

    if ($sinceLastCheckpoint -ge $CheckpointEveryNFiles) {
        $recordsWriter.Flush()
        Write-CheckpointAtomic -Path $CheckpointPath -Data @{
            RunId          = $RunId
            FilesProcessed = $filesProcessedCount
            TotalFiles     = $totalFiles
            ChainHash      = $lastChainHash
            ErrorCount     = $errorCount
            LastUpdateUtc  = (Get-Date).ToUniversalTime().ToString('o')
        }
        $sinceLastCheckpoint = 0
        $pct = [math]::Round(($filesProcessedCount / $totalFiles) * 100, 1)
        Write-Host "  Checkpoint : $filesProcessedCount / $totalFiles ($pct%) — erreurs: $errorCount"
    }
}

$recordsWriter.Flush()
$recordsWriter.Dispose()
$sha256Main.Dispose()

# Checkpoint final
Write-CheckpointAtomic -Path $CheckpointPath -Data @{
    RunId          = $RunId
    FilesProcessed = $filesProcessedCount
    TotalFiles     = $totalFiles
    ChainHash      = $lastChainHash
    ErrorCount     = $errorCount
    LastUpdateUtc  = (Get-Date).ToUniversalTime().ToString('o')
}

$duration = (Get-Date) - $startTime
Write-Host ""
Write-Host "Scan terminé en $($duration.ToString('hh\:mm\:ss')) — $filesProcessedCount fichiers, $errorCount erreurs." -ForegroundColor Green

# ============================================================
# 5. QUALITY GATES (FAIL-CLOSED)
# ============================================================

Write-Phase "QUALITY GATES"

$gates = [ordered]@{}
$allPathsInRecords = [System.Collections.Generic.HashSet[string]]::new()
$duplicateFound = $false
$sizeMismatchCount = 0

foreach ($line in [System.IO.File]::ReadLines($RecordsPath)) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $r = $line | ConvertFrom-Json
    if (-not $allPathsInRecords.Add($r.RelativePath)) { $duplicateFound = $true }
    if ($r.Status -eq 'SIZE_MISMATCH') { $sizeMismatchCount++ }
}

# G-01 : le nombre de records == nombre de fichiers découverts
$gates['G-01_RecordCountMatchesDiscovery'] = @{
    Pass     = ($allPathsInRecords.Count -eq $totalFiles)
    Expected = $totalFiles
    Actual   = $allPathsInRecords.Count
}

# G-02 : aucun chemin dupliqué
$gates['G-02_NoDuplicatePaths'] = @{
    Pass = (-not $duplicateFound)
}

# G-03 : aucune incohérence de taille (bytes lus == taille annoncée)
$gates['G-03_NoSizeMismatch'] = @{
    Pass  = ($sizeMismatchCount -eq 0)
    Count = $sizeMismatchCount
}

# G-04 : zéro erreur de lecture (sinon fail-closed strict — configurable si tu veux tolérer)
$gates['G-04_NoReadErrors'] = @{
    Pass  = ($errorCount -eq 0)
    Count = $errorCount
}

# G-05 : la chaîne finale recalculée correspond au checkpoint
$verifyChain = ''
$sha256Verify = [System.Security.Cryptography.SHA256]::Create()
foreach ($line in [System.IO.File]::ReadLines($RecordsPath)) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $r = $line | ConvertFrom-Json
    $toHash = "$verifyChain|$($r.RecordHash)"
    $hashBytes = $sha256Verify.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($toHash))
    $verifyChain = [System.BitConverter]::ToString($hashBytes).Replace('-', '').ToLowerInvariant()
}
$sha256Verify.Dispose()
$checkpointFinal = Get-Content -LiteralPath $CheckpointPath -Raw | ConvertFrom-Json
$gates['G-05_ChainIntegrityVerified'] = @{
    Pass     = ($verifyChain -eq $checkpointFinal.ChainHash)
    Expected = $checkpointFinal.ChainHash
    Actual   = $verifyChain
}

$allGatesPassed = -not ($gates.Values | Where-Object { -not $_.Pass })

$gatesReport = [ordered]@{
    RunId          = $RunId
    EvaluatedAtUtc = (Get-Date).ToUniversalTime().ToString('o')
    Gates          = $gates
    AllPassed      = $allGatesPassed
}
($gatesReport | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $GatesPath -Encoding UTF8

foreach ($g in $gates.GetEnumerator()) {
    $status = if ($g.Value.Pass) { 'PASS' } else { 'FAIL' }
    $color = if ($g.Value.Pass) { 'Green' } else { 'Red' }
    Write-Host "  [$status] $($g.Key)" -ForegroundColor $color
}

# ============================================================
# 6. COMMIT ATOMIQUE (seulement si TOUTES les gates passent)
# ============================================================

Write-Phase "CERTIFICATION"

$manifest = [ordered]@{
    RunId           = $RunId
    RootPathScanned = $RootPathCanon
    TotalFiles      = $totalFiles
    FilesProcessed  = $filesProcessedCount
    ErrorCount      = $errorCount
    ChainHash       = $lastChainHash
    CompletedAtUtc  = (Get-Date).ToUniversalTime().ToString('o')
    Certified       = $allGatesPassed
}
($manifest | ConvertTo-Json -Depth 5) | Set-Content -LiteralPath $ManifestPath -Encoding UTF8

if ($allGatesPassed) {
    New-Item -ItemType Directory -Path $FinalDir -Force | Out-Null
    Copy-Item -LiteralPath $RecordsPath, $CheckpointPath, $GatesPath, $ManifestPath -Destination $FinalDir -Force

    Write-Host ""
    Write-Host "CERTIFIED — le contenu de $RootPathCanon a été observé, prouvé et chaîné intégralement." -ForegroundColor Green
    Write-Host "Résultat final : $FinalDir"
    Write-Host "(le workspace transactionnel $TransactionRoot est conservé pour audit — supprime-le manuellement si tu n'en as plus besoin)"
}
else {
    Write-Host ""
    Write-Host "NON CERTIFIÉ — au moins une quality gate a échoué. Aucun commit vers la zone finale." -ForegroundColor Red
    Write-Host "Le workspace transactionnel est conservé intact pour investigation : $TransactionRoot"
    Write-Host "Détail des gates : $GatesPath"
    exit 1
}
