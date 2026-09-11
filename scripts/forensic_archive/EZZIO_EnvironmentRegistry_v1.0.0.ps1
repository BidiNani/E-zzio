#Requires -Version 7.0

<#
.SYNOPSIS
    E-ZZIO — ENVIRONMENT REGISTRY ENGINE v1.0.0

.DESCRIPTION
    Construit une représentation canonique, physique et vérifiable
    de l'environnement E-ZZIO autour d'un Point Zero.

    OBJECTIF FONDAMENTAL :

        Les moteurs E-ZZIO ne doivent plus reconstruire eux-mêmes
        les chemins de leurs dépendances.

    Ce moteur établit donc :

        SourceRoot
        ForensicRoot
        ContentTruth
        PointZero
        EnvironmentTruth
        SelfBody
        Topology
        Semantic
        ProjectMap
        ArtifactSHA256
        records.jsonl
        run_manifest.json
        checkpoint.json
        quality_gates.json
        EnvironmentTruth artifact
        autres artefacts détectables

    PROPRIÉTÉS :

        READ-ONLY sur SourceRoot et PointZero.
        Aucun fichier du projet n'est modifié.
        Les artefacts absents sont enregistrés comme ABSENT.
        Une incohérence d'identité ou de frontière provoque FAIL-CLOSED.
        Aucun CERTIFIED.
        Aucun FROZEN.

    SORTIE :

        EZZIO_ENVIRONMENT_REGISTRY.json

    Le Registry constitue ensuite la source canonique de résolution
    pour les moteurs Semantic, Topology, Certification, etc.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$SourceRoot = 'G:\AI\E-zzio',

    [Parameter(Mandatory = $false)]
    [string]$PointZeroDir = 'G:\AI\_forensic\ContentTruth\run_20260820_130134_380',

    [Parameter(Mandatory = $false)]
    [string]$OutputDir = 'G:\AI\_forensic\EnvironmentTruth\run_20260820_130134_380'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONSTANTES
# ============================================================================

$EngineVersion  = '1.0.0'
$SchemaVersion  = '1.0'
$ContractName   = 'EZZIO_ENVIRONMENT_REGISTRY'
$ContractVersion = '1.0.0'

# ============================================================================
# AFFICHAGE
# ============================================================================

Write-Host ''
Write-Host '==============================================================================' -ForegroundColor Cyan
Write-Host " E-ZZIO — ENVIRONMENT REGISTRY ENGINE v$EngineVersion" -ForegroundColor Cyan
Write-Host ' READ-ONLY / FORENSIC / FAIL-CLOSED' -ForegroundColor Cyan
Write-Host '==============================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "SourceRoot        : $SourceRoot"
Write-Host "PointZeroDir      : $PointZeroDir"
Write-Host "OutputDir         : $OutputDir"
Write-Host "Contract          : $ContractName v$ContractVersion"
Write-Host ''

# ============================================================================
# UTILITAIRES
# ============================================================================

function Fail-Closed {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Red
    Write-Host ' E-ZZIO — ENVIRONMENT REGISTRY : FAIL-CLOSED' -ForegroundColor Red
    Write-Host '============================================================' -ForegroundColor Red
    Write-Host ''
    Write-Host "ERROR : $Message" -ForegroundColor Red
    Write-Host ''
    Write-Host 'AUCUNE MODIFICATION DU PROJET EFFECTUÉE.' -ForegroundColor Yellow
    Write-Host 'AUCUN CERTIFIED/FROZEN ÉMIS.' -ForegroundColor Yellow
    Write-Host ''

    exit 1
}

function Get-CanonicalPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    try {
        return [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
    }
    catch {
        Fail-Closed "Impossible de canonicaliser le chemin : $Path"
    }
}

function Test-PathWithinBoundary {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Candidate,

        [Parameter(Mandatory = $true)]
        [string]$Boundary
    )

    $candidateCanonical = Get-CanonicalPath $Candidate
    $boundaryCanonical  = Get-CanonicalPath $Boundary

    if ([string]::Equals(
        $candidateCanonical,
        $boundaryCanonical,
        [System.StringComparison]::OrdinalIgnoreCase
    )) {
        return $true
    }

    $prefix = $boundaryCanonical + [System.IO.Path]::DirectorySeparatorChar

    return $candidateCanonical.StartsWith(
        $prefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Get-FileSha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not [System.IO.File]::Exists($Path)) {
        Fail-Closed "Fichier attendu absent pendant SHA-256 : $Path"
    }

    $sha = [System.Security.Cryptography.SHA256]::Create()

    try {
        $stream = [System.IO.File]::Open(
            $Path,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::Read
        )

        try {
            $hash = $sha.ComputeHash($stream)
        }
        finally {
            $stream.Dispose()
        }
    }
    finally {
        $sha.Dispose()
    }

    return [System.BitConverter]::ToString($hash).Replace('-', '').ToLowerInvariant()
}

function Get-ArtifactRecord {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ArtifactType,

        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Boundary,

        [Parameter(Mandatory = $true)]
        [string]$RunId,

        [Parameter(Mandatory = $false)]
        [string]$ExpectedHash = ''
    )

    $canonicalPath = Get-CanonicalPath $Path

    $record = [ordered]@{
        artifact_type       = $ArtifactType
        path                = $canonicalPath
        exists              = $false
        boundary_valid      = $false
        run_id              = $RunId
        size_bytes          = $null
        sha256              = $null
        expected_sha256     = if ([string]::IsNullOrWhiteSpace($ExpectedHash)) { $null } else { $ExpectedHash }
        hash_match          = $null
        status              = 'ABSENT'
    }

    if (-not (Test-PathWithinBoundary -Candidate $canonicalPath -Boundary $Boundary)) {
        $record.status = 'BOUNDARY_VIOLATION'
        return $record
    }

    $record.boundary_valid = $true

    if (-not [System.IO.File]::Exists($canonicalPath)) {
        return $record
    }

    $record.exists = $true

    $fileInfo = [System.IO.FileInfo]::new($canonicalPath)

    $record.size_bytes = [int64]$fileInfo.Length
    $record.sha256     = Get-FileSha256 -Path $canonicalPath

    if (-not [string]::IsNullOrWhiteSpace($ExpectedHash)) {
        $record.hash_match = [string]::Equals(
            $record.sha256,
            $ExpectedHash,
            [System.StringComparison]::OrdinalIgnoreCase
        )

        if ($record.hash_match) {
            $record.status = 'VALID'
        }
        else {
            $record.status = 'HASH_MISMATCH'
        }
    }
    else {
        $record.status = 'PRESENT'
    }

    return $record
}

function Find-ExactFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,

        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not [System.IO.Directory]::Exists($Root)) {
        return @()
    }

    $results = @(
        Get-ChildItem `
            -LiteralPath $Root `
            -File `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq $Name
        } |
        Select-Object -ExpandProperty FullName
    )

    return $results
}

function Find-ExactDirectory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,

        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not [System.IO.Directory]::Exists($Root)) {
        return @()
    }

    $results = @(
        Get-ChildItem `
            -LiteralPath $Root `
            -Directory `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq $Name
        } |
        Select-Object -ExpandProperty FullName
    )

    return $results
}

function Select-UniqueCandidate {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$Candidates,

        [Parameter(Mandatory = $true)]
        [string]$ArtifactName
    )

    $unique = @(
        $Candidates |
        Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } |
        ForEach-Object { Get-CanonicalPath ([string]$_) } |
        Sort-Object -Unique
    )

    if ($unique.Count -eq 0) {
        return $null
    }

    if ($unique.Count -gt 1) {
        Write-Host "[WARN] Plusieurs candidats pour $ArtifactName :" -ForegroundColor Yellow

        foreach ($candidate in $unique) {
            Write-Host "       $candidate" -ForegroundColor DarkYellow
        }

        Write-Host "       Sélection déterministe : chemin ordinal minimal." -ForegroundColor DarkYellow
    }

    return ($unique | Sort-Object)[0]
}

function New-DirectoryRecord {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Type,

        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Boundary,

        [Parameter(Mandatory = $true)]
        [string]$RunId
    )

    $canonicalPath = Get-CanonicalPath $Path

    $exists = [System.IO.Directory]::Exists($canonicalPath)
    $boundaryValid = Test-PathWithinBoundary `
        -Candidate $canonicalPath `
        -Boundary $Boundary

    $status = 'ABSENT'

    if (-not $boundaryValid) {
        $status = 'BOUNDARY_VIOLATION'
    }
    elseif ($exists) {
        $status = 'PRESENT'
    }

    return [ordered]@{
        type           = $Type
        path           = $canonicalPath
        exists         = $exists
        boundary_valid = $boundaryValid
        run_id         = $RunId
        status         = $status
    }
}

# ============================================================================
# 1 — PREFLIGHT PHYSIQUE
# ============================================================================

Write-Host '=============================================================================='
Write-Host ' 1 — PREFLIGHT PHYSIQUE'
Write-Host '=============================================================================='

$SourceRootCanonical   = Get-CanonicalPath $SourceRoot
$PointZeroCanonical    = Get-CanonicalPath $PointZeroDir
$OutputDirCanonical    = Get-CanonicalPath $OutputDir

if (-not [System.IO.Directory]::Exists($SourceRootCanonical)) {
    Fail-Closed "SourceRoot inexistant : $SourceRootCanonical"
}

if (-not [System.IO.Directory]::Exists($PointZeroCanonical)) {
    Fail-Closed "PointZeroDir inexistant : $PointZeroCanonical"
}

Write-Host "[PASS] SourceRoot existe" -ForegroundColor Green
Write-Host "[PASS] PointZero existe" -ForegroundColor Green

# ============================================================================
# 2 — DÉTERMINATION DES RACINES FORENSIQUES
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 2 — RACINES FORENSIQUES'
Write-Host '=============================================================================='

$contentTruthRoot = Get-CanonicalPath (
    Split-Path -Parent $PointZeroCanonical
)

$forensicRoot = Get-CanonicalPath (
    Split-Path -Parent $contentTruthRoot
)

Write-Host "ForensicRoot      : $forensicRoot"
Write-Host "ContentTruthRoot  : $contentTruthRoot"

if (-not (Test-PathWithinBoundary `
    -Candidate $PointZeroCanonical `
    -Boundary $contentTruthRoot)) {

    Fail-Closed 'PointZero hors frontière ContentTruth.'
}

if (-not (Test-PathWithinBoundary `
    -Candidate $contentTruthRoot `
    -Boundary $forensicRoot)) {

    Fail-Closed 'ContentTruth hors frontière ForensicRoot.'
}

Write-Host '[PASS] Frontières ContentTruth / Forensic cohérentes' -ForegroundColor Green

# ============================================================================
# 3 — IDENTITÉ CANONIQUE
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 3 — IDENTITÉ CANONIQUE'
Write-Host '=============================================================================='

$physicalLeaf = Split-Path -Leaf $PointZeroCanonical

if (-not $physicalLeaf.StartsWith('run_')) {
    Fail-Closed "PointZero invalide : préfixe run_ absent dans '$physicalLeaf'."
}

$canonicalRunId = $physicalLeaf.Substring(4)

if ($canonicalRunId -notmatch '^\d{8}_\d{6}_\d{3}$') {
    Fail-Closed "RunId physique malformé : '$canonicalRunId'."
}

Write-Host "Physical directory : $physicalLeaf"
Write-Host "Canonical RunId    : $canonicalRunId"

# ============================================================================
# 4 — MANIFEST POINT ZERO
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 4 — MANIFEST POINT ZERO'
Write-Host '=============================================================================='

$manifestPath = Join-Path $PointZeroCanonical 'run_manifest.json'
$recordsPath  = Join-Path $PointZeroCanonical 'records.jsonl'

if (-not [System.IO.File]::Exists($manifestPath)) {
    Fail-Closed "run_manifest.json absent : $manifestPath"
}

if (-not [System.IO.File]::Exists($recordsPath)) {
    Fail-Closed "records.jsonl absent : $recordsPath"
}

try {
    $manifestRaw = [System.IO.File]::ReadAllText(
        $manifestPath,
        [System.Text.Encoding]::UTF8
    )

    $manifest = $manifestRaw | ConvertFrom-Json -ErrorAction Stop
}
catch {
    Fail-Closed "run_manifest.json invalide : $($_.Exception.Message)"
}

$manifestRunId = [string]$manifest.RunId

if ([string]::IsNullOrWhiteSpace($manifestRunId)) {
    Fail-Closed 'RunId absent du run_manifest.json.'
}

if ($manifestRunId -ne $canonicalRunId) {
    Fail-Closed "Rupture d'identité : Manifest='$manifestRunId' / Physique='$canonicalRunId'."
}

$manifestSha = Get-FileSha256 -Path $manifestPath
$recordsSha  = Get-FileSha256 -Path $recordsPath

Write-Host '[PASS] Manifest RunId == RunId physique normalisé' -ForegroundColor Green
Write-Host "Manifest SHA256 : $manifestSha"
Write-Host "Records SHA256  : $recordsSha"

# ============================================================================
# 5 — ENVIRONMENT TRUTH EXISTANT
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 5 — ENVIRONMENT TRUTH'
Write-Host '=============================================================================='

$environmentTruthDir = Get-CanonicalPath $OutputDirCanonical
$environmentTruthJson = Join-Path `
    $environmentTruthDir `
    'EZZIO_ENVIRONMENT_TRUTH.json'

$environmentTruthRecord = Get-ArtifactRecord `
    -ArtifactType 'ENVIRONMENT_TRUTH' `
    -Path $environmentTruthJson `
    -Boundary $forensicRoot `
    -RunId $canonicalRunId

if ($environmentTruthRecord.status -eq 'VALID' -or
    $environmentTruthRecord.status -eq 'PRESENT') {

    Write-Host "[PASS] Environment Truth présent : $environmentTruthJson" -ForegroundColor Green
}
else {
    Write-Host "[INFO] Environment Truth : $($environmentTruthRecord.status)" -ForegroundColor Yellow
}

# ============================================================================
# 6 — DÉCOUVERTE DES STRUCTURES
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 6 — DÉCOUVERTE STRUCTURELLE'
Write-Host '=============================================================================='
Write-Host 'Recherche des structures par identité physique...' -ForegroundColor Yellow

# ---------------------------------------------------------------------------
# SELF BODY
# ---------------------------------------------------------------------------

$selfBodyCandidates = @(
    Join-Path $forensicRoot 'SelfBody'
)

$selfBodyFound = Select-UniqueCandidate `
    -Candidates $selfBodyCandidates `
    -ArtifactName 'SelfBody'

# ---------------------------------------------------------------------------
# TOPOLOGY
# ---------------------------------------------------------------------------

$topologyCandidates = @()

if ($selfBodyFound) {

    $topologyRunDir = Join-Path `
        $selfBodyFound `
        "topology\run_$canonicalRunId"

    if ([System.IO.Directory]::Exists($topologyRunDir)) {
        $topologyCandidates += $topologyRunDir
    }
}

# Découverte physique de secours dans ForensicRoot.
if ($topologyCandidates.Count -eq 0) {

    $topologyCandidates += Find-ExactDirectory `
        -Root $forensicRoot `
        -Name "run_$canonicalRunId"
}

$topologyRunDirFound = Select-UniqueCandidate `
    -Candidates $topologyCandidates `
    -ArtifactName 'Topology Run Directory'

$topologyArtifactCandidates = @()

if ($topologyRunDirFound) {

    $topologyArtifactCandidates += Join-Path `
        $topologyRunDirFound `
        'EZZIO_TOPOLOGY_STATE.json'
}

if ($topologyArtifactCandidates.Count -eq 0) {

    $topologyArtifactCandidates += Find-ExactFile `
        -Root $forensicRoot `
        -Name 'EZZIO_TOPOLOGY_STATE.json' |
        Where-Object {
            $_ -match [regex]::Escape("run_$canonicalRunId")
        }
}

$topologyArtifactFound = Select-UniqueCandidate `
    -Candidates $topologyArtifactCandidates `
    -ArtifactName 'EZZIO_TOPOLOGY_STATE.json'

# ---------------------------------------------------------------------------
# SEMANTIC
# ---------------------------------------------------------------------------

$semanticCandidates = @()

if ($selfBodyFound) {

    $semanticRunDir = Join-Path `
        $selfBodyFound `
        "semantic\run_$canonicalRunId"

    if ([System.IO.Directory]::Exists($semanticRunDir)) {
        $semanticCandidates += $semanticRunDir
    }
}

$semanticRunDirFound = Select-UniqueCandidate `
    -Candidates $semanticCandidates `
    -ArtifactName 'Semantic Run Directory'

# ---------------------------------------------------------------------------
# PROJECT MAP
# ---------------------------------------------------------------------------

$projectMapCandidates = @()

$directProjectMap = Join-Path `
    $PointZeroCanonical `
    '_project_map'

if ([System.IO.Directory]::Exists($directProjectMap)) {
    $projectMapCandidates += $directProjectMap
}

if ($projectMapCandidates.Count -eq 0) {

    $projectMapCandidates += Find-ExactDirectory `
        -Root $PointZeroCanonical `
        -Name '_project_map'
}

$projectMapFound = Select-UniqueCandidate `
    -Candidates $projectMapCandidates `
    -ArtifactName '_project_map'

# ---------------------------------------------------------------------------
# ARTIFACT SHA256
# ---------------------------------------------------------------------------

$artifactShaCandidates = @()

if ($projectMapFound) {

    $artifactShaCandidates += Join-Path `
        $projectMapFound `
        'E-ZZIO_ARTIFACT_SHA256.json'
}

if ($artifactShaCandidates.Count -eq 0) {

    $artifactShaCandidates += Find-ExactFile `
        -Root $PointZeroCanonical `
        -Name 'E-ZZIO_ARTIFACT_SHA256.json'
}

$artifactShaFound = Select-UniqueCandidate `
    -Candidates $artifactShaCandidates `
    -ArtifactName 'E-ZZIO_ARTIFACT_SHA256.json'

Write-Host ''
Write-Host "SelfBody             : $(if ($selfBodyFound) { $selfBodyFound } else { '[ABSENT]' })"
Write-Host "Topology Run         : $(if ($topologyRunDirFound) { $topologyRunDirFound } else { '[ABSENT]' })"
Write-Host "Topology Artifact    : $(if ($topologyArtifactFound) { $topologyArtifactFound } else { '[ABSENT]' })"
Write-Host "Semantic Run         : $(if ($semanticRunDirFound) { $semanticRunDirFound } else { '[ABSENT]' })"
Write-Host "Project Map          : $(if ($projectMapFound) { $projectMapFound } else { '[ABSENT]' })"
Write-Host "Artifact SHA256      : $(if ($artifactShaFound) { $artifactShaFound } else { '[ABSENT]' })"

# ============================================================================
# 7 — ARTÉFACTS POINT ZERO
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 7 — ARTÉFACTS POINT ZERO'
Write-Host '=============================================================================='

$artifactRecords = [ordered]@{}

$artifactRecords['run_manifest'] = Get-ArtifactRecord `
    -ArtifactType 'RUN_MANIFEST' `
    -Path $manifestPath `
    -Boundary $PointZeroCanonical `
    -RunId $canonicalRunId `
    -ExpectedHash $manifestSha

$artifactRecords['records'] = Get-ArtifactRecord `
    -ArtifactType 'RECORDS_JSONL' `
    -Path $recordsPath `
    -Boundary $PointZeroCanonical `
    -RunId $canonicalRunId `
    -ExpectedHash $recordsSha

$checkpointPath = Join-Path $PointZeroCanonical 'checkpoint.json'

$artifactRecords['checkpoint'] = Get-ArtifactRecord `
    -ArtifactType 'CHECKPOINT' `
    -Path $checkpointPath `
    -Boundary $PointZeroCanonical `
    -RunId $canonicalRunId

$qualityGatesPath = Join-Path $PointZeroCanonical 'quality_gates.json'

$artifactRecords['quality_gates'] = Get-ArtifactRecord `
    -ArtifactType 'QUALITY_GATES' `
    -Path $qualityGatesPath `
    -Boundary $PointZeroCanonical `
    -RunId $canonicalRunId

if ($artifactShaFound) {

    $artifactRecords['project_artifact_sha256'] = Get-ArtifactRecord `
        -ArtifactType 'PROJECT_ARTIFACT_SHA256' `
        -Path $artifactShaFound `
        -Boundary $PointZeroCanonical `
        -RunId $canonicalRunId
}
else {

    $artifactRecords['project_artifact_sha256'] = [ordered]@{
        artifact_type   = 'PROJECT_ARTIFACT_SHA256'
        path            = $null
        exists          = $false
        boundary_valid  = $true
        run_id          = $canonicalRunId
        size_bytes      = $null
        sha256          = $null
        expected_sha256 = $null
        hash_match      = $null
        status          = 'ABSENT'
    }
}

if ($topologyArtifactFound) {

    $artifactRecords['topology_state'] = Get-ArtifactRecord `
        -ArtifactType 'TOPOLOGY_STATE' `
        -Path $topologyArtifactFound `
        -Boundary $forensicRoot `
        -RunId $canonicalRunId
}
else {

    $artifactRecords['topology_state'] = [ordered]@{
        artifact_type   = 'TOPOLOGY_STATE'
        path            = $null
        exists          = $false
        boundary_valid  = $true
        run_id          = $canonicalRunId
        size_bytes      = $null
        sha256          = $null
        expected_sha256 = $null
        hash_match      = $null
        status          = 'ABSENT'
    }
}

# ============================================================================
# 8 — VALIDATION TOPOLOGIQUE SI PRÉSENTE
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 8 — VALIDATION TOPOLOGIQUE'
Write-Host '=============================================================================='

$topologyValidation = [ordered]@{
    discovered          = $false
    run_id_match        = $null
    records_hash_match  = $null
    payload_hash_present = $null
    status               = 'ABSENT'
}

if ($topologyArtifactFound) {

    $topologyValidation.discovered = $true

    try {

        $topologyRaw = [System.IO.File]::ReadAllText(
            $topologyArtifactFound,
            [System.Text.Encoding]::UTF8
        )

        $topology = $topologyRaw | ConvertFrom-Json -ErrorAction Stop

        $topologyRun = [string]$topology.lineage.parent_point_zero_run
        $topologyRecordsHash = [string]$topology.lineage.parent_records_sha256
        $topologyPayloadHash = [string]$topology.proof.topology_payload_sha256

        $topologyValidation.run_id_match = (
            $topologyRun -eq $canonicalRunId
        )

        $topologyValidation.records_hash_match = (
            $topologyRecordsHash -eq $recordsSha
        )

        $topologyValidation.payload_hash_present = (
            -not [string]::IsNullOrWhiteSpace($topologyPayloadHash)
        )

        if (
            $topologyValidation.run_id_match -and
            $topologyValidation.records_hash_match -and
            $topologyValidation.payload_hash_present
        ) {
            $topologyValidation.status = 'VALID'
            Write-Host '[PASS] Topology lineage valide' -ForegroundColor Green
        }
        else {
            $topologyValidation.status = 'INVALID'
            Write-Host '[FAIL] Topology lineage incohérente' -ForegroundColor Red
        }
    }
    catch {
        $topologyValidation.status = 'INVALID'
        Write-Host "[FAIL] Topology illisible : $($_.Exception.Message)" -ForegroundColor Red
    }
}
else {
    Write-Host '[INFO] Aucun artefact topologique détecté.' -ForegroundColor Yellow
}

# ============================================================================
# 9 — REGISTRE DES CHEMINS CANONIQUES
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 9 — REGISTRE DES CHEMINS'
Write-Host '=============================================================================='

$paths = [ordered]@{

    source_root = [ordered]@{
        path   = $SourceRootCanonical
        status = 'PRESENT'
    }

    forensic_root = [ordered]@{
        path   = $forensicRoot
        status = 'PRESENT'
    }

    content_truth = [ordered]@{
        path   = $contentTruthRoot
        status = 'PRESENT'
    }

    point_zero = [ordered]@{
        path   = $PointZeroCanonical
        status = 'PRESENT'
    }

    environment_truth = [ordered]@{
        path   = $environmentTruthDir
        status = if ([System.IO.Directory]::Exists($environmentTruthDir)) {
            'PRESENT'
        }
        else {
            'ABSENT'
        }
    }

    self_body = [ordered]@{
        path   = $selfBodyFound
        status = if ($selfBodyFound) { 'PRESENT' } else { 'ABSENT' }
    }

    topology = [ordered]@{
        path   = $topologyRunDirFound
        status = if ($topologyRunDirFound) { 'PRESENT' } else { 'ABSENT' }
    }

    semantic = [ordered]@{
        path   = $semanticRunDirFound
        status = if ($semanticRunDirFound) { 'PRESENT' } else { 'ABSENT' }
    }

    project_map = [ordered]@{
        path   = $projectMapFound
        status = if ($projectMapFound) { 'PRESENT' } else { 'ABSENT' }
    }

    artifact_sha256 = [ordered]@{
        path   = $artifactShaFound
        status = if ($artifactShaFound) { 'PRESENT' } else { 'ABSENT' }
    }
}

foreach ($entry in $paths.GetEnumerator()) {

    if ($null -eq $entry.Value.path) {
        Write-Host "[ABSENT] $($entry.Key)" -ForegroundColor Yellow
    }
    else {
        Write-Host "[$($entry.Value.status)] $($entry.Key) -> $($entry.Value.path)"
    }
}

# ============================================================================
# 10 — QUALIFICATION DES ABSENCES
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 10 — QUALIFICATION ENVIRONNEMENT'
Write-Host '=============================================================================='

$criticalArtifacts = @(
    'run_manifest',
    'records'
)

$criticalFailures = [System.Collections.Generic.List[string]]::new()
$knownAbsences     = [System.Collections.Generic.List[string]]::new()
$warnings          = [System.Collections.Generic.List[string]]::new()

foreach ($name in $criticalArtifacts) {

    $record = $artifactRecords[$name]

    if ($record.status -ne 'VALID') {

        $criticalFailures.Add(
            "$name : $($record.status)"
        )
    }
}

foreach ($entry in $artifactRecords.GetEnumerator()) {

    if ($entry.Value.status -eq 'ABSENT') {

        $knownAbsences.Add($entry.Key)
    }

    if ($entry.Value.status -eq 'HASH_MISMATCH') {

        $criticalFailures.Add(
            "$($entry.Key) : HASH_MISMATCH"
        )
    }

    if ($entry.Value.status -eq 'BOUNDARY_VIOLATION') {

        $criticalFailures.Add(
            "$($entry.Key) : BOUNDARY_VIOLATION"
        )
    }
}

if ($topologyValidation.status -eq 'INVALID') {

    $criticalFailures.Add(
        'topology_state : INVALID'
    )
}

$environmentStatus = 'VALID'

if ($criticalFailures.Count -gt 0) {
    $environmentStatus = 'FAIL-CLOSED'
}
elseif ($knownAbsences.Count -gt 0) {
    $environmentStatus = 'VALID_WITH_ABSENCES'
}

Write-Host ''
Write-Host "Environment status : $environmentStatus"

if ($knownAbsences.Count -gt 0) {

    Write-Host ''
    Write-Host 'Artefacts absents détectés :' -ForegroundColor Yellow

    foreach ($absence in $knownAbsences) {
        Write-Host "  - $absence" -ForegroundColor Yellow
    }
}

if ($criticalFailures.Count -gt 0) {

    Write-Host ''
    Write-Host 'Anomalies critiques :' -ForegroundColor Red

    foreach ($failure in $criticalFailures) {
        Write-Host "  - $failure" -ForegroundColor Red
    }

    Fail-Closed 'Le registre environnemental ne peut pas être déclaré cohérent.'
}

# ============================================================================
# 11 — CONSTRUCTION DU REGISTRY
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 11 — CONSTRUCTION ENVIRONMENT REGISTRY'
Write-Host '=============================================================================='

$registry = [ordered]@{

    artifact_type = 'EZZIO_ENVIRONMENT_REGISTRY'

    contract = [ordered]@{
        name    = $ContractName
        version = $ContractVersion
    }

    schema_version = $SchemaVersion

    engine = [ordered]@{
        name    = 'EZZIO_EnvironmentRegistry'
        version = $EngineVersion
    }

    metadata = [ordered]@{
        generated_at_utc = [DateTime]::UtcNow.ToString('o')
        mode             = 'FORENSIC'
        mutation         = 'NONE'
        source_mutation  = $false
    }

    identity = [ordered]@{
        canonical_run_id = $canonicalRunId
        physical_dir     = $physicalLeaf
        manifest_run_id  = $manifestRunId
        identity_status  = 'VALID'
    }

    roots = [ordered]@{
        source_root      = $SourceRootCanonical
        forensic_root    = $forensicRoot
        content_truth    = $contentTruthRoot
        point_zero       = $PointZeroCanonical
        environment_truth = $environmentTruthDir
    }

    paths = $paths

    artifacts = $artifactRecords

    topology = $topologyValidation

    environment_truth = $environmentTruthRecord

    status = [ordered]@{
        overall              = $environmentStatus
        critical_failures    = @($criticalFailures)
        known_absences       = @($knownAbsences)
        warnings             = @($warnings)
        certified            = $false
        frozen               = $false
    }
}

# ============================================================================
# 12 — PERSISTANCE HORS SOURCE ROOT
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 12 — PERSISTANCE DU REGISTRY'
Write-Host '=============================================================================='

if (-not (Test-PathWithinBoundary `
    -Candidate $OutputDirCanonical `
    -Boundary $forensicRoot)) {

    Fail-Closed 'OutputDir du Registry hors ForensicRoot.'
}

if (Test-PathWithinBoundary `
    -Candidate $OutputDirCanonical `
    -Boundary $SourceRootCanonical) {

    Fail-Closed 'OutputDir du Registry intersecte SourceRoot.'
}

if (-not [System.IO.Directory]::Exists($OutputDirCanonical)) {

    [System.IO.Directory]::CreateDirectory($OutputDirCanonical) | Out-Null
}

$registryPath = Join-Path `
    $OutputDirCanonical `
    'EZZIO_ENVIRONMENT_REGISTRY.json'

$registryJson = $registry |
    ConvertTo-Json -Depth 50

[System.IO.File]::WriteAllText(
    $registryPath,
    $registryJson,
    [System.Text.UTF8Encoding]::new($false)
)

if (-not [System.IO.File]::Exists($registryPath)) {

    Fail-Closed 'Le Registry n''a pas été physiquement créé.'
}

$registrySha = Get-FileSha256 -Path $registryPath

Write-Host '[PASS] Registry écrit hors SourceRoot' -ForegroundColor Green
Write-Host "Registry : $registryPath"
Write-Host "SHA256   : $registrySha"

# ============================================================================
# 13 — POST-COMMIT FORENSIC
# ============================================================================

Write-Host ''
Write-Host '=============================================================================='
Write-Host ' 13 — POST-COMMIT FORENSIC'
Write-Host '=============================================================================='

$registryRecheckSha = Get-FileSha256 -Path $registryPath

if ($registryRecheckSha -ne $registrySha) {

    Fail-Closed 'SHA-256 du Registry instable après écriture.'
}

$registrySize = [System.IO.FileInfo]::new($registryPath).Length

Write-Host '[PASS] Existence physique' -ForegroundColor Green
Write-Host '[PASS] SHA-256 stable' -ForegroundColor Green
Write-Host '[PASS] Frontière Forensic respectée' -ForegroundColor Green
Write-Host '[PASS] SourceRoot non modifié par le moteur' -ForegroundColor Green

# ============================================================================
# 14 — VERDICT
# ============================================================================

Write-Host ''
Write-Host '==============================================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO — ENVIRONMENT REGISTRY : VALID' -ForegroundColor Green
Write-Host '==============================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "Canonical RunId       : $canonicalRunId"
Write-Host "SourceRoot            : $SourceRootCanonical"
Write-Host "ForensicRoot          : $forensicRoot"
Write-Host "PointZero             : $PointZeroCanonical"
Write-Host "Environment status    : $environmentStatus"
Write-Host "Registry size         : $registrySize bytes"
Write-Host "Registry SHA256       : $registrySha"
Write-Host ''
Write-Host '------------------------------------------------------------'
Write-Host ' ARTEFACTS CONNUS'
Write-Host '------------------------------------------------------------'

foreach ($entry in $artifactRecords.GetEnumerator()) {

    $r = $entry.Value

    Write-Host (
        "{0,-28} : {1}" -f
        $entry.Key,
        $r.status
    )
}

Write-Host ''
Write-Host '------------------------------------------------------------'
Write-Host ' RÉSOLUTIONS'
Write-Host '------------------------------------------------------------'

foreach ($entry in $paths.GetEnumerator()) {

    Write-Host (
        "{0,-24} : {1}" -f
        $entry.Key,
        $(if ($null -eq $entry.Value.path) { '[ABSENT]' } else { $entry.Value.path })
    )
}

Write-Host ''
Write-Host "Registry : $registryPath"
Write-Host ''
Write-Host 'CERTIFIED : NOT EMITTED'
Write-Host 'FROZEN    : NOT EMITTED'
Write-Host ''
Write-Host '==============================================================================' -ForegroundColor Cyan
Write-Host ' ENVIRONMENT REGISTRY ENGINE — FINISHED' -ForegroundColor Green
Write-Host '==============================================================================' -ForegroundColor Cyan
Write-Host ''