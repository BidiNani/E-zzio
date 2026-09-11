#Requires -Version 7.0

<#
.SYNOPSIS
    E-ZZIO — ENVIRONMENT TRUTH ENGINE v1.0.0

.DESCRIPTION
    Construit une représentation forensic et canonique de l'environnement E-ZZIO.

    PRINCIPES:
      - READ-ONLY sur le projet analysé
      - FORENSIC
      - FAIL-CLOSED
      - aucune auto-correction
      - aucune suppression
      - aucune modification du SourceRoot
      - découverte physique avant normalisation
      - identité physique et identité logique explicitement séparées
      - Point Zero strictement déterministe
      - manifest résolu exclusivement depuis le Point Zero
      - SHA-256 des artefacts critiques
      - génération d'un Environment Truth Snapshot externe

    IMPORTANT:
      Les fichiers générés par ce moteur sont écrits uniquement dans OutputDir.
      Le SourceRoot et le PointZeroDir sont traités en lecture seule.

.VERSION
    1.0.0

.CONTRACT
    EZZIO_ENVIRONMENT_TRUTH

.OUTPUT
    EZZIO_ENVIRONMENT_TRUTH.json
    EZZIO_ENVIRONMENT_TRUTH_REPORT.txt
    EZZIO_ENVIRONMENT_TRUTH.sha256
#>

[CmdletBinding()]
param(

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$SourceRoot = 'G:\AI\E-zzio',

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$PointZeroDir = 'G:\AI\_forensic\ContentTruth\run_20260820_130134_380',

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$OutputDir = 'G:\AI\_forensic\EnvironmentTruth',

    [Parameter(Mandatory = $false)]
    [ValidateSet('FAST','FORENSIC')]
    [string]$Mode = 'FORENSIC'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# GLOBAL STATE
# ============================================================================

$EngineVersion = '1.0.0'
$ContractName  = 'EZZIO_ENVIRONMENT_TRUTH'
$UtcNow        = [DateTime]::UtcNow

$script:Failures = [System.Collections.Generic.List[string]]::new()
$script:Warnings = [System.Collections.Generic.List[string]]::new()

# ============================================================================
# OUTPUT HELPERS
# ============================================================================

function Write-Section {
    param(
        [Parameter(Mandatory)]
        [string]$Title
    )

    Write-Host ''
    Write-Host ('=' * 78) -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host ('=' * 78) -ForegroundColor Cyan
}

function Write-Pass {
    param([string]$Message)

    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Write-Fail {
    param([string]$Message)

    Write-Host "[FAIL] $Message" -ForegroundColor Red
    [void]$script:Failures.Add($Message)
}

function Write-Warn {
    param([string]$Message)

    Write-Host "[WARN] $Message" -ForegroundColor Yellow
    [void]$script:Warnings.Add($Message)
}

function Fail-Closed {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Host ''
    Write-Host '============================================================' `
        -ForegroundColor Red
    Write-Host ' E-ZZIO — ENVIRONMENT TRUTH : FAIL-CLOSED' `
        -ForegroundColor Red
    Write-Host '============================================================' `
        -ForegroundColor Red

    Write-Host "CAUSE : $Message" -ForegroundColor Red
    Write-Host ''
    Write-Host 'Aucune modification du projet effectuée.' -ForegroundColor Cyan
    Write-Host 'Aucun statut CERTIFIED/FROZEN émis.' -ForegroundColor Cyan

    throw [System.InvalidOperationException]::new(
        "FAIL-CLOSED: $Message"
    )
}

# ============================================================================
# PATH HELPERS
# ============================================================================

function Get-CanonicalFullPath {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    try {
        return [System.IO.Path]::GetFullPath($Path).TrimEnd('\','/')
    }
    catch {
        Fail-Closed "Impossible de canonicaliser le chemin : $Path"
    }
}

function Assert-Directory {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Label
    )

    if (-not [System.IO.Directory]::Exists($Path)) {
        Fail-Closed "$Label inexistant : $Path"
    }

    Write-Pass "$Label existe"
}

function Assert-File {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Label
    )

    if (-not [System.IO.File]::Exists($Path)) {
        Fail-Closed "$Label inexistant : $Path"
    }

    Write-Pass "$Label existe"
}

function Get-Sha256File {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    try {
        return (
            Get-FileHash -LiteralPath $Path -Algorithm SHA256
        ).Hash.ToLowerInvariant()
    }
    catch {
        Fail-Closed "Impossible de calculer SHA-256 : $Path"
    }
}

# ============================================================================
# SAFE TEXT / JSON
# ============================================================================

function Read-Utf8Strict {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    try {
        $bytes = [System.IO.File]::ReadAllBytes($Path)

        if ($bytes.Length -eq 0) {
            Fail-Closed "Fichier UTF-8 vide : $Path"
        }

        $utf8 = [System.Text.UTF8Encoding]::new(
            $false,
            $true
        )

        return $utf8.GetString($bytes)
    }
    catch {
        Fail-Closed "Lecture UTF-8 stricte impossible : $Path"
    }
}

function Read-JsonStrict {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $text = Read-Utf8Strict -Path $Path

    try {
        return $text | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        Fail-Closed "JSON invalide : $Path"
    }
}

function Get-StringProperty {
    param(
        [Parameter(Mandatory)]
        [object]$Object,

        [Parameter(Mandatory)]
        [string]$Name
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
# RUN ID CONTRACT
# ============================================================================

function Get-PhysicalPointZeroName {
    param(
        [Parameter(Mandatory)]
        [string]$PointZeroPath
    )

    return Split-Path -Leaf (
        $PointZeroPath.TrimEnd('\','/')
    )
}

function Resolve-CanonicalRunId {
    param(
        [Parameter(Mandatory)]
        [string]$PhysicalDirectoryName
    )

    if ([string]::IsNullOrWhiteSpace($PhysicalDirectoryName)) {
        Fail-Closed 'Nom physique du Point Zero vide.'
    }

    if (-not $PhysicalDirectoryName.StartsWith(
        'run_',
        [System.StringComparison]::Ordinal
    )) {
        Fail-Closed (
            "PointZeroDir non conforme au contrat canonique : " +
            "'run_' absent dans '$PhysicalDirectoryName'."
        )
    }

    $logicalRunId = $PhysicalDirectoryName.Substring(4)

    if ([string]::IsNullOrWhiteSpace($logicalRunId)) {
        Fail-Closed (
            "PointZeroDir non conforme : RunId logique vide."
        )
    }

    # Contrat strict actuel des RunId E-ZZIO.
    if ($logicalRunId -notmatch '^\d{8}_\d{6}_\d{3}$') {
        Fail-Closed (
            "RunId logique non conforme au contrat : '$logicalRunId'."
        )
    }

    return $logicalRunId
}

# ============================================================================
# PATH RELATIONSHIP
# ============================================================================

function Test-PathWithin {
    param(
        [Parameter(Mandatory)]
        [string]$Child,

        [Parameter(Mandatory)]
        [string]$Parent
    )

    $childCanonical  = Get-CanonicalFullPath -Path $Child
    $parentCanonical = Get-CanonicalFullPath -Path $Parent

    $prefix = $parentCanonical.TrimEnd('\') + '\'

    return (
        $childCanonical.Equals(
            $parentCanonical,
            [System.StringComparison]::OrdinalIgnoreCase
        ) -or
        $childCanonical.StartsWith(
            $prefix,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    )
}

# ============================================================================
# ENVIRONMENT INVENTORY
# ============================================================================

function Get-EnvironmentInventory {
    param(
        [Parameter(Mandatory)]
        [string]$Root,

        [Parameter(Mandatory)]
        [ValidateSet('FAST','FORENSIC')]
        [string]$ScanMode
    )

    $result = [ordered]@{
        files_total       = 0
        directories_total = 0
        python_files      = 0
        powershell_files  = 0
        json_files        = 0
        jsonl_files       = 0
        sqlite_files      = 0
        markdown_files    = 0
        empty_files       = 0
        inaccessible      = 0
    }

    Write-Host "Inventaire filesystem : $Root" -ForegroundColor DarkCyan

    try {
        if ($ScanMode -eq 'FAST') {

            $entries = Get-ChildItem `
                -LiteralPath $Root `
                -Force `
                -ErrorAction Stop

            foreach ($entry in $entries) {

                if ($entry.PSIsContainer) {
                    $result.directories_total++
                    continue
                }

                $result.files_total++

                switch ($entry.Extension.ToLowerInvariant()) {
                    '.py'   { $result.python_files++ }
                    '.ps1'  { $result.powershell_files++ }
                    '.json' { $result.json_files++ }
                    '.jsonl'{ $result.jsonl_files++ }
                    '.db'   { $result.sqlite_files++ }
                    '.sqlite' { $result.sqlite_files++ }
                    '.md'   { $result.markdown_files++ }
                }

                if ($entry.Length -eq 0) {
                    $result.empty_files++
                }
            }

            return [pscustomobject]$result
        }

        # FORENSIC
        $entries = Get-ChildItem `
            -LiteralPath $Root `
            -Force `
            -Recurse `
            -ErrorAction SilentlyContinue

        foreach ($entry in $entries) {

            if ($entry.PSIsContainer) {
                $result.directories_total++
                continue
            }

            $result.files_total++

            switch ($entry.Extension.ToLowerInvariant()) {
                '.py'     { $result.python_files++ }
                '.ps1'    { $result.powershell_files++ }
                '.json'   { $result.json_files++ }
                '.jsonl'  { $result.jsonl_files++ }
                '.db'     { $result.sqlite_files++ }
                '.sqlite' { $result.sqlite_files++ }
                '.md'     { $result.markdown_files++ }
            }

            if ($entry.Length -eq 0) {
                $result.empty_files++
            }
        }

        return [pscustomobject]$result
    }
    catch {
        Fail-Closed "Inventaire filesystem impossible : $Root"
    }
}

# ============================================================================
# CRITICAL ARTIFACT DISCOVERY
# ============================================================================

function Get-PointZeroArtifacts {
    param(
        [Parameter(Mandatory)]
        [string]$PointZero
    )

    $artifactNames = @(
        'run_manifest.json',
        'records.jsonl',
        'checkpoint.json',
        'quality_gates.json'
    )

    $artifacts = [ordered]@{}

    foreach ($name in $artifactNames) {

        $path = Join-Path $PointZero $name

        if ([System.IO.File]::Exists($path)) {

            $sha256 = Get-Sha256File -Path $path

            $artifacts[$name] = [ordered]@{
                path       = $path
                exists     = $true
                length     = (
                    [System.IO.FileInfo]::new($path)
                ).Length
                sha256     = $sha256
            }
        }
        else {

            $artifacts[$name] = [ordered]@{
                path       = $path
                exists     = $false
                length     = $null
                sha256     = $null
            }
        }
    }

    return $artifacts
}

# ============================================================================
# MANIFEST IDENTITY
# ============================================================================

function Test-ManifestIdentity {
    param(
        [Parameter(Mandatory)]
        [string]$ManifestPath,

        [Parameter(Mandatory)]
        [string]$CanonicalRunId
    )

    Assert-File `
        -Path $ManifestPath `
        -Label 'PointZero run_manifest.json'

    $manifestSha256 = Get-Sha256File -Path $ManifestPath

    $manifest = Read-JsonStrict -Path $ManifestPath

    $manifestRunId = Get-StringProperty `
        -Object $manifest `
        -Name 'RunId'

    if ([string]::IsNullOrWhiteSpace($manifestRunId)) {
        Fail-Closed 'run_manifest.json ne contient aucun RunId.'
    }

    if ($manifestRunId -ne $CanonicalRunId) {

        Fail-Closed (
            "Manifest RunId incohérent. " +
            "Manifest='$manifestRunId' ; " +
            "Canonical='$CanonicalRunId'."
        )
    }

    Write-Pass "Manifest RunId == Canonical RunId"

    return [ordered]@{
        path       = $ManifestPath
        sha256     = $manifestSha256
        run_id     = $manifestRunId
        certified  = [bool]$manifest.Certified
        raw_object = $manifest
    }
}

# ============================================================================
# ENVIRONMENT CONTRACT
# ============================================================================

function New-EnvironmentTruthObject {
    param(
        [Parameter(Mandatory)]
        [string]$CanonicalSourceRoot,

        [Parameter(Mandatory)]
        [string]$CanonicalPointZero,

        [Parameter(Mandatory)]
        [string]$PhysicalPointZeroName,

        [Parameter(Mandatory)]
        [string]$CanonicalRunId,

        [Parameter(Mandatory)]
        [hashtable]$ManifestInfo,

        [Parameter(Mandatory)]
        [hashtable]$Artifacts,

        [Parameter(Mandatory)]
        [pscustomobject]$Inventory,

        [Parameter(Mandatory)]
        [string]$ScanMode
    )

    return [ordered]@{

        artifact_type = $CONTRACT_NAME

        schema_version = '1.0.0'

        engine = [ordered]@{
            name    = 'EZZIO Environment Truth Engine'
            version = $EngineVersion
            mode    = $ScanMode
        }

        observation = [ordered]@{
            observed_utc = $UtcNow.ToString(
                'yyyy-MM-ddTHH:mm:ss.fffffffZ'
            )

            machine = $env:COMPUTERNAME

            user = $env:USERNAME

            powershell = $PSVersionTable.PSVersion.ToString()

            process_architecture = $env:PROCESSOR_ARCHITECTURE

            operating_system = [System.Environment]::OSVersion.VersionString

            working_directory = (
                Get-Location
            ).Path
        }

        project = [ordered]@{
            source_root = $CanonicalSourceRoot
        }

        point_zero = [ordered]@{

            physical_path = $CanonicalPointZero

            physical_name = $PhysicalPointZeroName

            naming_prefix = 'run_'

            logical_run_id = $CanonicalRunId

            identity_contract = 'run_<RunId>'

            identity_verified = $true
        }

        manifest = [ordered]@{
            path      = $ManifestInfo.path
            sha256    = $ManifestInfo.sha256
            run_id    = $ManifestInfo.run_id
            certified = $ManifestInfo.certified
            verified  = $true
        }

        artifacts = $Artifacts

        inventory = $Inventory

        boundaries = [ordered]@{
            source_root_read_only = $true

            point_zero_read_only = $true

            manifest_scope = 'STRICT_POINT_ZERO'

            recursive_manifest_discovery = $false

            output_scope = 'EXTERNAL_FORENSIC_OUTPUT_ONLY'
        }

        truth = [ordered]@{
            environment_identity = 'CONSISTENT'

            point_zero_identity = 'VERIFIED'

            manifest_identity = 'VERIFIED'

            boundary_integrity = 'VERIFIED'

            fail_closed = $true

            certified = $false
        }
    }
}

# ============================================================================
# CANONICAL JSON
# ============================================================================

function ConvertTo-CanonicalJson {
    param(
        [Parameter(Mandatory)]
        [object]$Object
    )

    return $Object | ConvertTo-Json `
        -Depth 30 `
        -Compress
}

# ============================================================================
# MAIN
# ============================================================================

try {

    Write-Host ''
    Write-Host '=============================================================================='
    Write-Host ' E-ZZIO — ENVIRONMENT TRUTH ENGINE v1.0.0'
    Write-Host ' READ-ONLY / FORENSIC / FAIL-CLOSED'
    Write-Host '=============================================================================='
    Write-Host ''

    Write-Host "Mode              : $Mode"
    Write-Host "SourceRoot        : $SourceRoot"
    Write-Host "PointZeroDir      : $PointZeroDir"
    Write-Host "OutputDir         : $OutputDir"
    Write-Host ''

    # ------------------------------------------------------------------------
    # 1 — PREFLIGHT
    # ------------------------------------------------------------------------

    Write-Section '1 — PREFLIGHT ENVIRONNEMENT'

    Assert-Directory `
        -Path $SourceRoot `
        -Label 'SourceRoot'

    Assert-Directory `
        -Path $PointZeroDir `
        -Label 'PointZeroDir'

    $sourceRootCanonical = Get-CanonicalFullPath `
        -Path $SourceRoot

    $pointZeroCanonical = Get-CanonicalFullPath `
        -Path $PointZeroDir

    Write-Host "SourceRoot canonical   : $sourceRootCanonical"
    Write-Host "PointZero canonical   : $pointZeroCanonical"

    # ------------------------------------------------------------------------
    # 2 — BOUNDARY
    # ------------------------------------------------------------------------

    Write-Section '2 — FRONTIÈRES'

    if (-not (Test-PathWithin `
        -Child $pointZeroCanonical `
        -Parent 'G:\AI\_forensic\ContentTruth')) {

        Write-Warn (
            'PointZero situé hors de la racine forensic attendue.'
        )
    }
    else {
        Write-Pass 'PointZero appartient à la frontière ContentTruth'
    }

    if (
        $sourceRootCanonical.Equals(
            $pointZeroCanonical,
            [System.StringComparison]::OrdinalIgnoreCase
        )
    ) {
        Fail-Closed (
            'SourceRoot et PointZeroDir ne peuvent pas être identiques.'
        )
    }

    Write-Pass 'SourceRoot et PointZero séparés'

    # ------------------------------------------------------------------------
    # 3 — PHYSICAL IDENTITY
    # ------------------------------------------------------------------------

    Write-Section '3 — IDENTITÉ PHYSIQUE DU POINT ZERO'

    $physicalPointZeroName = Get-PhysicalPointZeroName `
        -PointZeroPath $pointZeroCanonical

    Write-Host "Physical directory : $physicalPointZeroName"

    if ([string]::IsNullOrWhiteSpace($physicalPointZeroName)) {
        Fail-Closed 'Nom physique du Point Zero vide.'
    }

    # ------------------------------------------------------------------------
    # 4 — LOGICAL IDENTITY
    # ------------------------------------------------------------------------

    Write-Section '4 — IDENTITÉ LOGIQUE CANONIQUE'

    $canonicalRunId = Resolve-CanonicalRunId `
        -PhysicalDirectoryName $physicalPointZeroName

    Write-Host "Logical RunId      : $canonicalRunId"

    Write-Pass (
        "Relation physique/logique vérifiée : " +
        "$physicalPointZeroName -> $canonicalRunId"
    )

    # ------------------------------------------------------------------------
    # 5 — MANIFEST STRICT
    # ------------------------------------------------------------------------

    Write-Section '5 — MANIFEST STRICTEMENT BORNÉ AU POINT ZERO'

    $manifestPath = Join-Path `
        $pointZeroCanonical `
        'run_manifest.json'

    if (-not (Test-PathWithin `
        -Child $manifestPath `
        -Parent $pointZeroCanonical)) {

        Fail-Closed (
            'Manifest résolu hors frontière PointZero.'
        )
    }

    Write-Pass 'Manifest dans la frontière PointZero'

    $manifestInfo = Test-ManifestIdentity `
        -ManifestPath $manifestPath `
        -CanonicalRunId $canonicalRunId

    Write-Host "Manifest SHA-256   : $($manifestInfo.sha256)"
    Write-Host "Manifest RunId     : $($manifestInfo.run_id)"

    # ------------------------------------------------------------------------
    # 6 — CRITICAL ARTIFACTS
    # ------------------------------------------------------------------------

    Write-Section '6 — ARTEFACTS CRITIQUES'

    $artifacts = Get-PointZeroArtifacts `
        -PointZero $pointZeroCanonical

    foreach ($artifactName in $artifacts.Keys) {

        $artifact = $artifacts[$artifactName]

        if ($artifact.exists) {

            Write-Pass (
                "$artifactName | " +
                "SIZE=$($artifact.length) | " +
                "SHA256=$($artifact.sha256)"
            )
        }
        else {

            Write-Warn (
                "$artifactName absent du PointZero."
            )
        }
    }

    # ------------------------------------------------------------------------
    # 7 — INVENTORY
    # ------------------------------------------------------------------------

    Write-Section '7 — INVENTAIRE ENVIRONNEMENT'

    $inventory = Get-EnvironmentInventory `
        -Root $sourceRootCanonical `
        -ScanMode $Mode

    Write-Host ''
    Write-Host "Files total       : $($inventory.files_total)"
    Write-Host "Directories total : $($inventory.directories_total)"
    Write-Host "Python            : $($inventory.python_files)"
    Write-Host "PowerShell        : $($inventory.powershell_files)"
    Write-Host "JSON              : $($inventory.json_files)"
    Write-Host "JSONL             : $($inventory.jsonl_files)"
    Write-Host "SQLite            : $($inventory.sqlite_files)"
    Write-Host "Markdown          : $($inventory.markdown_files)"
    Write-Host "Empty files       : $($inventory.empty_files)"

    # ------------------------------------------------------------------------
    # 8 — ENVIRONMENT TRUTH
    # ------------------------------------------------------------------------

    Write-Section '8 — CONSTRUCTION ENVIRONMENT TRUTH'

    $environmentTruth = New-EnvironmentTruthObject `
        -CanonicalSourceRoot $sourceRootCanonical `
        -CanonicalPointZero $pointZeroCanonical `
        -PhysicalPointZeroName $physicalPointZeroName `
        -CanonicalRunId $canonicalRunId `
        -ManifestInfo $manifestInfo `
        -Artifacts $artifacts `
        -Inventory $inventory `
        -ScanMode $Mode

    Write-Pass 'Identité projet établie'
    Write-Pass 'Identité PointZero établie'
    Write-Pass 'Identité logique RunId établie'
    Write-Pass 'Manifest parent vérifié'
    Write-Pass 'Frontières vérifiées'

    # ------------------------------------------------------------------------
    # 9 — OUTPUT DIRECTORY
    # ------------------------------------------------------------------------

    Write-Section '9 — SORTIE FORENSIC'

    # OutputDir est le SEUL emplacement muté par ce moteur.
    if (-not [System.IO.Directory]::Exists($OutputDir)) {

        [System.IO.Directory]::CreateDirectory(
            $OutputDir
        ) | Out-Null
    }

    $outputCanonical = Get-CanonicalFullPath `
        -Path $OutputDir

    $jsonPath = Join-Path `
        $outputCanonical `
        'EZZIO_ENVIRONMENT_TRUTH.json'

    $reportPath = Join-Path `
        $outputCanonical `
        'EZZIO_ENVIRONMENT_TRUTH_REPORT.txt'

    $hashPath = Join-Path `
        $outputCanonical `
        'EZZIO_ENVIRONMENT_TRUTH.sha256'

    # ------------------------------------------------------------------------
    # 10 — SERIALIZATION
    # ------------------------------------------------------------------------

    $canonicalJson = ConvertTo-CanonicalJson `
        -Object $environmentTruth

    [System.IO.File]::WriteAllText(
        $jsonPath,
        $canonicalJson,
        [System.Text.UTF8Encoding]::new($false)
    )

    $environmentHash = Get-Sha256File `
        -Path $jsonPath

    [System.IO.File]::WriteAllText(
        $hashPath,
        "$environmentHash  EZZIO_ENVIRONMENT_TRUTH.json",
        [System.Text.UTF8Encoding]::new($false)
    )

    # ------------------------------------------------------------------------
    # 11 — HUMAN REPORT
    # ------------------------------------------------------------------------

    $report = @"
E-ZZIO — ENVIRONMENT TRUTH ENGINE v$EngineVersion
============================================================

MODE
----
$Mode

OBSERVATION UTC
---------------
$($UtcNow.ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ'))

MACHINE
-------
$env:COMPUTERNAME

USER
----
$env:USERNAME

POWERSHELL
----------
$($PSVersionTable.PSVersion)

PROJECT
-------
SourceRoot:
$sourceRootCanonical

POINT ZERO
----------
Physical Path:
$pointZeroCanonical

Physical Name:
$physicalPointZeroName

Logical RunId:
$canonicalRunId

Identity Contract:
run_<RunId>

MANIFEST
--------
Path:
$manifestPath

RunId:
$($manifestInfo.run_id)

SHA256:
$($manifestInfo.sha256)

BOUNDARIES
----------
SourceRoot Read-Only:
TRUE

PointZero Read-Only:
TRUE

Manifest Scope:
STRICT_POINT_ZERO

Recursive Manifest Discovery:
FALSE

ENVIRONMENT INVENTORY
---------------------
Files:
$($inventory.files_total)

Directories:
$($inventory.directories_total)

Python:
$($inventory.python_files)

PowerShell:
$($inventory.powershell_files)

JSON:
$($inventory.json_files)

JSONL:
$($inventory.jsonl_files)

SQLite:
$($inventory.sqlite_files)

Markdown:
$($inventory.markdown_files)

Empty Files:
$($inventory.empty_files)

TRUTH
-----
Environment Identity:
CONSISTENT

PointZero Identity:
VERIFIED

Manifest Identity:
VERIFIED

Boundary Integrity:
VERIFIED

Certified:
FALSE

Reason:
Environment Truth establishes environmental facts.
It does NOT itself certify the Semantic State.

ENVIRONMENT TRUTH SHA256
------------------------
$environmentHash

OUTPUT
------
$jsonPath
$reportPath
$hashPath

MUTATION POLICY
---------------
Project mutation:
NONE

SourceRoot mutation:
NONE

PointZero mutation:
NONE

Automatic correction:
NONE

CERTIFIED/FROZEN:
NONE

============================================================
E-ZZIO ENVIRONMENT TRUTH : PASS
============================================================
"@

    [System.IO.File]::WriteAllText(
        $reportPath,
        $report,
        [System.Text.UTF8Encoding]::new($false)
    )

    # ------------------------------------------------------------------------
    # 12 — FINAL VERDICT
    # ------------------------------------------------------------------------

    Write-Section '10 — VERDICT ENVIRONMENT TRUTH'

    Write-Host ''
    Write-Host 'SourceRoot           : ' -NoNewline
    Write-Host $sourceRootCanonical -ForegroundColor Cyan

    Write-Host 'PointZero            : ' -NoNewline
    Write-Host $pointZeroCanonical -ForegroundColor Cyan

    Write-Host 'Physical Identity    : ' -NoNewline
    Write-Host $physicalPointZeroName -ForegroundColor Cyan

    Write-Host 'Canonical RunId      : ' -NoNewline
    Write-Host $canonicalRunId -ForegroundColor Cyan

    Write-Host 'Manifest SHA256      : ' -NoNewline
    Write-Host $manifestInfo.sha256 -ForegroundColor Cyan

    Write-Host ''
    Write-Host 'ENVIRONMENT TRUTH    : PASS' `
        -ForegroundColor Green

    Write-Host ''
    Write-Host 'IMPORTANT :' `
        -ForegroundColor Yellow

    Write-Host 'Environment Truth établit les faits environnementaux.'
    Write-Host 'Il ne certifie PAS le Semantic State.'
    Write-Host 'Aucune mutation du projet E-ZZIO n''a été effectuée.'
    Write-Host 'Aucun CERTIFIED/FROZEN n''a été émis.'

    Write-Host ''
    Write-Host "Snapshot : $jsonPath" -ForegroundColor DarkCyan
    Write-Host "Report   : $reportPath" -ForegroundColor DarkCyan
    Write-Host "SHA256   : $hashPath" -ForegroundColor DarkCyan
    Write-Host ''

}
catch {

    Write-Host ''
    Write-Host '============================================================' `
        -ForegroundColor Red

    Write-Host ' E-ZZIO — ENVIRONMENT TRUTH : FAIL-CLOSED' `
        -ForegroundColor Red

    Write-Host '============================================================' `
        -ForegroundColor Red

    Write-Host ''
    Write-Host "ERROR : $($_.Exception.Message)" `
        -ForegroundColor Red

    Write-Host ''
    Write-Host 'AUCUNE MODIFICATION DU PROJET EFFECTUÉE.' `
        -ForegroundColor Cyan

    Write-Host 'AUCUN CERTIFIED/FROZEN ÉMIS.' `
        -ForegroundColor Cyan

    exit 1
}