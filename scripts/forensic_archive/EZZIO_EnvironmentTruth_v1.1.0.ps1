#Requires -Version 7.0

<#
.SYNOPSIS
    E-ZZIO — ENVIRONMENT TRUTH ENGINE v1.1.0

.DESCRIPTION
    Moteur de connaissance environnementale déterministe.

    Principes :
      - READ-ONLY
      - FORENSIC
      - FAIL-CLOSED
      - aucune découverte récursive de manifestes
      - PointZero = source d'identité primaire
      - identité physique et logique séparées explicitement
      - aucune variable implicite
      - aucune émission CERTIFIED/FROZEN

    Le moteur établit :
      1. l'existence des frontières
      2. l'identité physique du Point Zero
      3. l'identité logique canonique
      4. le manifeste strictement borné
      5. les artefacts critiques
      6. l'inventaire filesystem
      7. un Environment Truth report

    IMPORTANT :
      Ce moteur ne modifie jamais SourceRoot.
      Le seul artefact éventuellement écrit est le rapport dans OutputDir.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('FAST','FORENSIC')]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,

    [Parameter(Mandatory = $true)]
    [string]$PointZeroDir,

    [Parameter(Mandatory = $true)]
    [string]$OutputDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONSTANTES — TOUTES EXPLICITES
# ============================================================================

$EngineName    = 'E-ZZIO — ENVIRONMENT TRUTH ENGINE'
$EngineVersion = '1.1.0'
$ContractName  = 'EZZIO_ENVIRONMENT_TRUTH'
$ContractVersion = '1.0.0'

$Script:Failures = [System.Collections.Generic.List[string]]::new()
$Script:Warnings = [System.Collections.Generic.List[string]]::new()

# ============================================================================
# UTILITAIRES
# ============================================================================

function Write-Section {
    param([Parameter(Mandatory)][string]$Title)

    Write-Host ''
    Write-Host ('=' * 78) -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host ('=' * 78) -ForegroundColor Cyan
}

function Pass {
    param([Parameter(Mandatory)][string]$Message)

    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Warn {
    param([Parameter(Mandatory)][string]$Message)

    $Script:Warnings.Add($Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Fail-Closed {
    param([Parameter(Mandatory)][string]$Message)

    $Script:Failures.Add($Message)

    Write-Host ''
    Write-Host ('=' * 78) -ForegroundColor Red
    Write-Host " E-ZZIO — ENVIRONMENT TRUTH : FAIL-CLOSED" -ForegroundColor Red
    Write-Host ('=' * 78) -ForegroundColor Red
    Write-Host ''
    Write-Host "ERROR : $Message" -ForegroundColor Red
    Write-Host ''
    Write-Host 'AUCUNE MODIFICATION DU PROJET EFFECTUÉE.' -ForegroundColor Yellow
    Write-Host 'AUCUN CERTIFIED/FROZEN ÉMIS.' -ForegroundColor Yellow
    Write-Host ''

    exit 1
}

function Get-CanonicalDirectory {
    param([Parameter(Mandatory)][string]$Path)

    if (-not [System.IO.Directory]::Exists($Path)) {
        throw "Directory inexistante : $Path"
    }

    return [System.IO.Path]::GetFullPath($Path).TrimEnd('\','/')
}

function Get-CanonicalFile {
    param([Parameter(Mandatory)][string]$Path)

    if (-not [System.IO.File]::Exists($Path)) {
        throw "Fichier inexistant : $Path"
    }

    return [System.IO.Path]::GetFullPath($Path)
}

function Get-Sha256File {
    param([Parameter(Mandatory)][string]$Path)

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Read-Utf8Strict {
    param([Parameter(Mandatory)][string]$Path)

    $bytes = [System.IO.File]::ReadAllBytes($Path)

    if ($bytes.Length -eq 0) {
        throw "Fichier vide : $Path"
    }

    return [System.Text.UTF8Encoding]::new(
        $false,
        $true
    ).GetString($bytes)
}

function Get-CanonicalRunId {
    param([Parameter(Mandatory)][string]$PointZeroCanonical)

    $leaf = [System.IO.Path]::GetFileName(
        $PointZeroCanonical.TrimEnd('\','/')
    )

    if ($leaf -notmatch '^run_(\d{8}_\d{6}_\d{3})$') {
        throw "Nom PointZero non conforme au contrat canonique : $leaf"
    }

    return $Matches[1]
}

function Test-IsWithinBoundary {
    param(
        [Parameter(Mandatory)][string]$Candidate,
        [Parameter(Mandatory)][string]$Boundary
    )

    $candidateFull = [System.IO.Path]::GetFullPath($Candidate).TrimEnd('\','/')
    $boundaryFull = [System.IO.Path]::GetFullPath($Boundary).TrimEnd('\','/')

    if ($candidateFull.Equals($boundaryFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $true
    }

    return $candidateFull.StartsWith(
        $boundaryFull + '\',
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Get-JsonPropertyString {
    param(
        [Parameter(Mandatory)]$Object,
        [Parameter(Mandatory)][string]$Name
    )

    $property = $Object.PSObject.Properties[$Name]

    if ($null -eq $property) {
        return $null
    }

    if ($null -eq $property.Value) {
        return $null
    }

    return [string]$property.Value
}

# ============================================================================
# HEADER
# ============================================================================

Write-Host ''
Write-Host ('=' * 78) -ForegroundColor Cyan
Write-Host " $EngineName v$EngineVersion" -ForegroundColor Cyan
Write-Host ' READ-ONLY / FORENSIC / FAIL-CLOSED' -ForegroundColor Cyan
Write-Host ('=' * 78) -ForegroundColor Cyan

Write-Host ''
Write-Host "Mode              : $Mode"
Write-Host "SourceRoot        : $SourceRoot"
Write-Host "PointZeroDir      : $PointZeroDir"
Write-Host "OutputDir         : $OutputDir"
Write-Host "Contract          : $ContractName v$ContractVersion"

# ============================================================================
# 1 — PREFLIGHT
# ============================================================================

Write-Section '1 — PREFLIGHT ENVIRONNEMENT'

if (-not [System.IO.Directory]::Exists($SourceRoot)) {
    Fail-Closed "SourceRoot inaccessible : $SourceRoot"
}

if (-not [System.IO.Directory]::Exists($PointZeroDir)) {
    Fail-Closed "PointZeroDir inaccessible : $PointZeroDir"
}

$SourceRootCanonical = Get-CanonicalDirectory $SourceRoot
$PointZeroCanonical  = Get-CanonicalDirectory $PointZeroDir

Pass 'SourceRoot existe'
Pass 'PointZeroDir existe'

Write-Host "SourceRoot canonical   : $SourceRootCanonical"
Write-Host "PointZero canonical    : $PointZeroCanonical"

# ============================================================================
# 2 — FRONTIÈRES
# ============================================================================

Write-Section '2 — FRONTIÈRES'

$ContentTruthBoundary = Get-CanonicalDirectory (
    Split-Path -Parent $PointZeroCanonical
)

if (-not (Test-IsWithinBoundary `
    -Candidate $PointZeroCanonical `
    -Boundary $ContentTruthBoundary)) {

    Fail-Closed 'PointZero hors frontière ContentTruth.'
}

Pass 'PointZero appartient à la frontière ContentTruth'

if ($SourceRootCanonical.Equals(
    $PointZeroCanonical,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    Fail-Closed 'SourceRoot et PointZero sont identiques.'
}

Pass 'SourceRoot et PointZero séparés'

# ============================================================================
# 3 — IDENTITÉ PHYSIQUE
# ============================================================================

Write-Section '3 — IDENTITÉ PHYSIQUE DU POINT ZERO'

$PhysicalDirectory = [System.IO.Path]::GetFileName(
    $PointZeroCanonical.TrimEnd('\','/')
)

Write-Host "Physical directory : $PhysicalDirectory"

# ============================================================================
# 4 — IDENTITÉ LOGIQUE CANONIQUE
# ============================================================================

Write-Section '4 — IDENTITÉ LOGIQUE CANONIQUE'

try {
    $CanonicalRunId = Get-CanonicalRunId $PointZeroCanonical
}
catch {
    Fail-Closed $_.Exception.Message
}

Write-Host "Logical RunId      : $CanonicalRunId"

$ExpectedPhysicalName = "run_$CanonicalRunId"

if ($PhysicalDirectory -ne $ExpectedPhysicalName) {
    Fail-Closed (
        "Identité physique/logique incohérente : " +
        "$PhysicalDirectory != $ExpectedPhysicalName"
    )
}

Pass "Relation physique/logique vérifiée : $PhysicalDirectory -> $CanonicalRunId"

# ============================================================================
# 5 — MANIFEST STRICTEMENT BORNÉ
# ============================================================================

Write-Section '5 — MANIFEST STRICTEMENT BORNÉ AU POINT ZERO'

# --------------------------------------------------------------------------
# CONTRAT CRITIQUE :
#
# Le moteur NE CHERCHE PAS un manifest.
# Il CONNAÎT son emplacement.
#
# PointZeroDir\run_manifest.json
# --------------------------------------------------------------------------

$ManifestPath = Join-Path $PointZeroCanonical 'run_manifest.json'

if (-not (Test-IsWithinBoundary `
    -Candidate $ManifestPath `
    -Boundary $PointZeroCanonical)) {

    Fail-Closed 'Manifest hors frontière PointZero.'
}

Pass 'Manifest dans la frontière PointZero'

if (-not [System.IO.File]::Exists($ManifestPath)) {
    Fail-Closed "PointZero run_manifest.json absent : $ManifestPath"
}

Pass 'PointZero run_manifest.json existe'

$ManifestCanonical = Get-CanonicalFile $ManifestPath

if ($ManifestCanonical -ne $ManifestPath) {
    Fail-Closed 'Résolution physique du manifest non canonique.'
}

$ManifestText = Read-Utf8Strict $ManifestCanonical

try {
    $ParentManifest = $ManifestText | ConvertFrom-Json -ErrorAction Stop
}
catch {
    Fail-Closed "Manifest JSON invalide : $($_.Exception.Message)"
}

$ManifestRunId = Get-JsonPropertyString `
    -Object $ParentManifest `
    -Name 'RunId'

if ([string]::IsNullOrWhiteSpace($ManifestRunId)) {
    Fail-Closed 'RunId absent du manifest PointZero.'
}

if ($ManifestRunId -ne $CanonicalRunId) {
    Fail-Closed (
        "RunId manifest incohérent : " +
        "$ManifestRunId != $CanonicalRunId"
    )
}

Pass 'Manifest RunId == Canonical RunId'

$ManifestSha256 = Get-Sha256File $ManifestCanonical

Write-Host "Manifest SHA-256   : $ManifestSha256"
Write-Host "Manifest RunId     : $ManifestRunId"

# ============================================================================
# 6 — ARTEFACTS CRITIQUES
# ============================================================================

Write-Section '6 — ARTEFACTS CRITIQUES'

$CriticalArtifacts = @(
    'run_manifest.json',
    'records.jsonl',
    'checkpoint.json',
    'quality_gates.json'
)

$ArtifactInventory = [System.Collections.Generic.List[object]]::new()

foreach ($artifactName in $CriticalArtifacts) {

    $artifactPath = Join-Path $PointZeroCanonical $artifactName

    if (-not [System.IO.File]::Exists($artifactPath)) {
        Fail-Closed "Artefact critique absent : $artifactName"
    }

    if (-not (Test-IsWithinBoundary `
        -Candidate $artifactPath `
        -Boundary $PointZeroCanonical)) {

        Fail-Closed "Artefact hors frontière : $artifactName"
    }

    $fileInfo = [System.IO.FileInfo]$artifactPath
    $sha = Get-Sha256File $artifactPath

    $ArtifactInventory.Add(
        [ordered]@{
            name       = $artifactName
            path       = $artifactPath
            size_bytes = [int64]$fileInfo.Length
            sha256     = $sha
        }
    )

    Pass (
        "{0} | SIZE={1} | SHA256={2}" -f
        $artifactName,
        $fileInfo.Length,
        $sha
    )
}

# ============================================================================
# 7 — INVENTAIRE ENVIRONNEMENT
# ============================================================================

Write-Section '7 — INVENTAIRE ENVIRONNEMENT'

Write-Host 'Inventaire filesystem : ' -NoNewline
Write-Host $SourceRootCanonical -ForegroundColor Cyan

Write-Host ''
Write-Host 'Analyse récursive READ-ONLY...'

$Files = @(
    Get-ChildItem `
        -LiteralPath $SourceRootCanonical `
        -File `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue
)

$Directories = @(
    Get-ChildItem `
        -LiteralPath $SourceRootCanonical `
        -Directory `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue
)

$FilesTotal       = $Files.Count
$DirectoriesTotal = $Directories.Count

$PythonCount = @(
    $Files | Where-Object {
        $_.Extension -ieq '.py'
    }
).Count

$PowerShellCount = @(
    $Files | Where-Object {
        $_.Extension -ieq '.ps1'
    }
).Count

$JsonCount = @(
    $Files | Where-Object {
        $_.Extension -ieq '.json'
    }
).Count

$JsonlCount = @(
    $Files | Where-Object {
        $_.Extension -ieq '.jsonl'
    }
).Count

$SqliteCount = @(
    $Files | Where-Object {
        $_.Extension -in @('.db','.sqlite','.sqlite3')
    }
).Count

$MarkdownCount = @(
    $Files | Where-Object {
        $_.Extension -in @('.md','.markdown')
    }
).Count

$EmptyCount = @(
    $Files | Where-Object {
        $_.Length -eq 0
    }
).Count

Write-Host ''
Write-Host "Files total       : $FilesTotal"
Write-Host "Directories total : $DirectoriesTotal"
Write-Host "Python            : $PythonCount"
Write-Host "PowerShell        : $PowerShellCount"
Write-Host "JSON              : $JsonCount"
Write-Host "JSONL             : $JsonlCount"
Write-Host "SQLite            : $SqliteCount"
Write-Host "Markdown          : $MarkdownCount"
Write-Host "Empty files       : $EmptyCount"

# ============================================================================
# 8 — ENVIRONMENT TRUTH
# ============================================================================

Write-Section '8 — CONSTRUCTION ENVIRONMENT TRUTH'

$EnvironmentTruth = [ordered]@{
    artifact_type       = 'EZZIO_ENVIRONMENT_TRUTH'
    schema_version      = '1.0.0'
    engine              = $EngineName
    engine_version      = $EngineVersion
    contract_name       = $ContractName
    contract_version    = $ContractVersion

    execution = [ordered]@{
        mode               = $Mode
        powershell_version = $PSVersionTable.PSVersion.ToString()
        machine            = $env:COMPUTERNAME
        user               = $env:USERNAME
        generated_utc      = [DateTime]::UtcNow.ToString(
            'yyyy-MM-ddTHH:mm:ss.fffZ'
        )
    }

    boundaries = [ordered]@{
        source_root        = $SourceRootCanonical
        content_truth_root = $ContentTruthBoundary
        point_zero         = $PointZeroCanonical
        output_dir         = $OutputDir
    }

    identity = [ordered]@{
        physical_directory = $PhysicalDirectory
        canonical_run_id    = $CanonicalRunId
        manifest_run_id     = $ManifestRunId
        identity_valid      = $true
    }

    point_zero = [ordered]@{
        manifest_path = $ManifestCanonical
        manifest_sha256 = $ManifestSha256
    }

    filesystem = [ordered]@{
        files_total       = $FilesTotal
        directories_total = $DirectoriesTotal
        python            = $PythonCount
        powershell        = $PowerShellCount
        json              = $JsonCount
        jsonl              = $JsonlCount
        sqlite            = $SqliteCount
        markdown          = $MarkdownCount
        empty_files       = $EmptyCount
    }

    critical_artifacts = @($ArtifactInventory)

    guarantees = [ordered]@{
        read_only          = $true
        fail_closed        = $true
        recursive_manifest_discovery = $false
        manifest_search_scope = 'PointZeroDir ONLY'
        certified_emitted  = $false
        frozen_emitted     = $false
        project_mutated    = $false
    }
}

# ============================================================================
# 9 — ÉCRITURE DU RAPPORT
# ============================================================================

Write-Section '9 — PERSISTANCE DU ENVIRONMENT TRUTH'

# L'OutputDir est EXTERNE au projet.
# Sa création ne constitue pas une mutation du projet E-ZZIO.

if (-not [System.IO.Directory]::Exists($OutputDir)) {
    [System.IO.Directory]::CreateDirectory($OutputDir) | Out-Null
}

$OutputCanonical = Get-CanonicalDirectory $OutputDir

if (Test-IsWithinBoundary `
    -Candidate $OutputCanonical `
    -Boundary $SourceRootCanonical) {

    Fail-Closed (
        'OutputDir se trouve dans SourceRoot. ' +
        'Refus de produire un artefact dans le projet.'
    )
}

$EnvironmentTruthPath = Join-Path `
    $OutputCanonical `
    'EZZIO_ENVIRONMENT_TRUTH.json'

$EnvironmentTruthJson = $EnvironmentTruth |
    ConvertTo-Json -Depth 20

[System.IO.File]::WriteAllText(
    $EnvironmentTruthPath,
    $EnvironmentTruthJson,
    [System.Text.UTF8Encoding]::new($false)
)

$EnvironmentTruthSha256 = Get-Sha256File $EnvironmentTruthPath

Pass 'Environment Truth écrit hors SourceRoot'

Write-Host "Artifact : $EnvironmentTruthPath"
Write-Host "SHA256   : $EnvironmentTruthSha256"

# ============================================================================
# 10 — VERDICT
# ============================================================================

Write-Section '10 — VERDICT ENVIRONMENT TRUTH'

if ($Script:Failures.Count -gt 0) {
    Fail-Closed (
        'Une ou plusieurs invariantes environnementales ont échoué.'
    )
}

Write-Host ''
Write-Host 'ENVIRONMENT TRUTH : VALID' -ForegroundColor Green
Write-Host ''
Write-Host "Canonical RunId    : $CanonicalRunId"
Write-Host "Physical directory : $PhysicalDirectory"
Write-Host "Manifest SHA256    : $ManifestSha256"
Write-Host "Files              : $FilesTotal"
Write-Host "Directories        : $DirectoriesTotal"
Write-Host ''
Write-Host 'Manifest discovery : POINTZERO-ONLY' -ForegroundColor Green
Write-Host 'Project mutation   : NONE' -ForegroundColor Green
Write-Host 'CERTIFIED           : NOT EMITTED' -ForegroundColor Yellow
Write-Host 'FROZEN              : NOT EMITTED' -ForegroundColor Yellow
Write-Host ''

Write-Host ('=' * 78) -ForegroundColor Cyan
Write-Host ' ENVIRONMENT TRUTH ENGINE — FINISHED' -ForegroundColor Cyan
Write-Host ('=' * 78) -ForegroundColor Cyan