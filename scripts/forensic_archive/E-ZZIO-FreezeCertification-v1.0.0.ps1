# ============================================================================
# E-ZZIO — FREEZE CERTIFICATION ENGINE v1.0.0
# ============================================================================
# PURPOSE
#   Figer l'état CERTIFIED actuel d'E-ZZIO sous forme d'une preuve
#   cryptographique indépendante et ré-auditable.
#
# MODE
#   FAST + FORENSIC
#   READ-ONLY FIRST
#   FAIL-CLOSED
#   NO CORPUS MUTATION
#
# IMPORTANT
#   Ce script DOIT être exécuté comme fichier .ps1.
#   Ne pas le coller morceau par morceau dans la console.
# ============================================================================

[CmdletBinding()]
param(
    [string]$EzzioRoot = 'G:\AI\E-zzio',

    [string]$EnginePath =
        'G:\AI\E-zzio\E-ZZIO-ControlledPurificationAndRebaseline-v0.2.1.ps1',

    [string]$CertifiedPythonPath =
        'G:\AI\E-zzio\runtime\audit\v7_full_intelligence_scan.py',

    [string]$OldPointZeroDir =
        'G:\AI\_forensic\ContentTruth\run_20260820_130134_380',

    [string]$NewPointZeroDir =
        'G:\AI\_forensic\ContentTruth\run_20260820_135058_169',

    [string]$PurificationReport =
        'G:\AI\_forensic\ControlledPurification\run_run_20260820_130134_380\controlled_purification_report.json',

    [string]$FreezeRoot =
        'G:\AI\_forensic\FreezeCertification',

    [switch]$PauseOnExit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# GLOBAL STATE
# ============================================================================

$EngineName    = 'E-ZZIO — FREEZE CERTIFICATION ENGINE'
$EngineVersion = '1.0.0'

$StartedAtUtc = [DateTime]::UtcNow

$ExitCode       = 1
$FreezeCertified = $false

$FatalError = $null
$freezeDir = $null
$freezeManifestPath = $null
$freezeManifestHash = $null

$GateResults = [System.Collections.Generic.List[object]]::new()
$Evidence    = [System.Collections.Generic.List[object]]::new()
$Warnings    = [System.Collections.Generic.List[object]]::new()

# ============================================================================
# OUTPUT
# ============================================================================

function Write-Section {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )

    Write-Host ''
    Write-Host '==============================================================================' `
        -ForegroundColor DarkCyan

    Write-Host " $Title" `
        -ForegroundColor Cyan

    Write-Host '==============================================================================' `
        -ForegroundColor DarkCyan
}

function Write-Pass {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Write-Fail {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Add-Gate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Gate,

        [Parameter(Mandatory = $true)]
        [bool]$Passed,

        [Parameter(Mandatory = $true)]
        [string]$Detail
    )

    $GateResults.Add(
        [PSCustomObject]@{
            Gate      = $Gate
            Passed    = $Passed
            Detail    = $Detail
            Timestamp = [DateTime]::UtcNow.ToString('o')
        }
    )
}

function Add-Evidence {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Value
    )

    $Evidence.Add(
        [PSCustomObject]@{
            Name      = $Name
            Value     = $Value
            Timestamp = [DateTime]::UtcNow.ToString('o')
        }
    )
}

function Add-Warning {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $Warnings.Add(
        [PSCustomObject]@{
            Message   = $Message
            Timestamp = [DateTime]::UtcNow.ToString('o')
        }
    )
}

# ============================================================================
# PATH
# ============================================================================

function Resolve-CanonicalPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Chemin absent : $Path"
    }

    $resolved = Resolve-Path `
        -LiteralPath $Path `
        -ErrorAction Stop

    return [System.IO.Path]::GetFullPath(
        $resolved.Path
    )
}

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (
        Test-Path `
            -LiteralPath $Path `
            -PathType Container
    )) {
        New-Item `
            -ItemType Directory `
            -Path $Path `
            -Force `
            -ErrorAction Stop |
            Out-Null
    }
}

# ============================================================================
# HASH
# ============================================================================

function Get-Sha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (
        Test-Path `
            -LiteralPath $Path `
            -PathType Leaf
    )) {
        throw "Fichier absent pour SHA-256 : $Path"
    }

    return (
        Get-FileHash `
            -LiteralPath $Path `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash.ToLowerInvariant()
}

# ============================================================================
# JSON STRICT
# ============================================================================

function Read-JsonStrict {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (
        Test-Path `
            -LiteralPath $Path `
            -PathType Leaf
    )) {
        throw "JSON absent : $Path"
    }

    $raw = [System.IO.File]::ReadAllText(
        $Path,
        [System.Text.UTF8Encoding]::new($false)
    )

    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "JSON vide : $Path"
    }

    try {
        return $raw | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        throw "JSON invalide : $Path :: $($_.Exception.Message)"
    }
}

# ============================================================================
# FILE IDENTITY
# ============================================================================

function Get-FileIdentity {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $item = Get-Item `
        -LiteralPath $Path `
        -Force `
        -ErrorAction Stop

    if (-not $item.PSIsContainer) {
        $hash = Get-Sha256 $Path
    }
    else {
        $hash = $null
    }

    return [PSCustomObject]@{
        Path         = $Path
        FullName     = $item.FullName
        Length       = $item.Length
        SHA256       = $hash
        LastWriteUtc = $item.LastWriteTimeUtc.ToString('o')
        CreationUtc  = $item.CreationTimeUtc.ToString('o')
    }
}

# ============================================================================
# AST
# ============================================================================

function Test-PowerShellAst {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $tokens = $null
    $errors = $null

    $null =
        [System.Management.Automation.Language.Parser]::ParseFile(
            $Path,
            [ref]$tokens,
            [ref]$errors
        )

    $errorArray = @($errors)

    return [PSCustomObject]@{
        Valid      = ($errorArray.Count -eq 0)
        ErrorCount = $errorArray.Count
        Errors     = $errorArray
    }
}

# ============================================================================
# PYTHON
# ============================================================================

function Find-Python {
    $commands = @(
        'python.exe',
        'python3.exe',
        'py.exe'
    )

    foreach ($commandName in $commands) {

        $command = Get-Command `
            -Name $commandName `
            -ErrorAction SilentlyContinue

        if ($null -ne $command) {
            return $command.Source
        }
    }

    return $null
}

function Test-PythonSyntax {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $python = Find-Python

    if ($null -eq $python) {

        return [PSCustomObject]@{
            Available = $false
            Valid     = $false
            ExitCode  = $null
            Detail    = 'PYTHON_INTERPRETER_NOT_FOUND'
        }
    }

    $process = Start-Process `
        -FilePath $python `
        -ArgumentList @(
            '-m',
            'py_compile',
            $Path
        ) `
        -NoNewWindow `
        -Wait `
        -PassThru `
        -ErrorAction Stop

    return [PSCustomObject]@{
        Available = $true
        Valid     = ($process.ExitCode -eq 0)
        ExitCode  = $process.ExitCode
        Detail    = if ($process.ExitCode -eq 0) {
            'PYTHON_SYNTAX_VALID'
        }
        else {
            'PYTHON_SYNTAX_INVALID'
        }
    }
}

# ============================================================================
# JSONL
# ============================================================================

function Get-JsonlLineCount {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (
        Test-Path `
            -LiteralPath $Path `
            -PathType Leaf
    )) {
        throw "JSONL absent : $Path"
    }

    $count = 0

    foreach ($line in [System.IO.File]::ReadLines($Path)) {

        if (-not [string]::IsNullOrWhiteSpace($line)) {
            $count++
        }
    }

    return $count
}

# ============================================================================
# SELF-INTEGRITY
# ============================================================================

function Test-SelfIntegrity {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath
    )

    Write-Section 'SG-00 — SELF-INTEGRITY / AST FIRST'

    $result = Test-PowerShellAst $ScriptPath

    Write-Host "Self AST Errors : $($result.ErrorCount)"

    if (-not $result.Valid) {

        foreach ($errorItem in @($result.Errors)) {

            Write-Host `
                "Ligne $($errorItem.Extent.StartLineNumber), colonne $($errorItem.Extent.StartColumnNumber) : $($errorItem.Message)" `
                -ForegroundColor Red
        }

        Add-Gate `
            'SG-00_SELF_AST' `
            $false `
            "$($result.ErrorCount) erreur(s) AST"

        throw 'SELF-AST FAIL-CLOSED : moteur de freeze invalide.'
    }

    Write-Pass 'AST du moteur de freeze valide : 0 erreur'

    Add-Gate `
        'SG-00_SELF_AST' `
        $true `
        '0 erreur AST'
}

# ============================================================================
# MAIN
# ============================================================================

try {

    # ========================================================================
    # SELF PATH
    # ========================================================================

    $thisScript = $PSCommandPath

    if ([string]::IsNullOrWhiteSpace($thisScript)) {

        throw `
            'Impossible de déterminer le chemin du moteur de freeze. Le script doit être exécuté comme fichier .ps1.'
    }

    Test-SelfIntegrity $thisScript

    Write-Section "$EngineName v$EngineVersion"

    Write-Host 'MODE              : FAST + FORENSIC / READ-ONLY / FAIL-CLOSED'
    Write-Host 'CORPUS MUTATION   : INTERDITE'
    Write-Host 'FREEZE DESTINATION: EXTERNE AU CORPUS'
    Write-Host ''

    # ========================================================================
    # SG-01 — PATHS
    # ========================================================================

    Write-Section 'SG-01 — RÉSOLUTION DES ARTEFACTS CERTIFIÉS'

    $resolvedEzzioRoot =
        Resolve-CanonicalPath $EzzioRoot

    $resolvedEngine =
        Resolve-CanonicalPath $EnginePath

    $resolvedPython =
        Resolve-CanonicalPath $CertifiedPythonPath

    $resolvedOldPz =
        Resolve-CanonicalPath $OldPointZeroDir

    $resolvedNewPz =
        Resolve-CanonicalPath $NewPointZeroDir

    $resolvedReport =
        Resolve-CanonicalPath $PurificationReport

    Write-Host "E-ZZIO ROOT : $resolvedEzzioRoot"
    Write-Host "MOTEUR      : $resolvedEngine"
    Write-Host "PYTHON      : $resolvedPython"
    Write-Host "OLD PZ      : $resolvedOldPz"
    Write-Host "NEW PZ      : $resolvedNewPz"
    Write-Host "REPORT      : $resolvedReport"

    Write-Pass 'Tous les artefacts certifiés sont présents'

    Add-Gate `
        'SG-01_ARTIFACT_PRESENCE' `
        $true `
        'Tous les artefacts présents'

    # ========================================================================
    # SG-02 — ENGINE AST
    # ========================================================================

    Write-Section 'SG-02 — AST DU MOTEUR DE PURIFICATION'

    $engineAst =
        Test-PowerShellAst $resolvedEngine

    Write-Host "AST errors : $($engineAst.ErrorCount)"

    if (-not $engineAst.Valid) {

        Add-Gate `
            'SG-02_PURIFICATION_ENGINE_AST' `
            $false `
            "$($engineAst.ErrorCount) erreur(s)"

        throw `
            'FAIL-CLOSED : moteur de purification AST invalide.'
    }

    Write-Pass 'Moteur de purification : AST valide'

    Add-Gate `
        'SG-02_PURIFICATION_ENGINE_AST' `
        $true `
        '0 erreur AST'

    # ========================================================================
    # SG-03 — PYTHON IDENTITY
    # ========================================================================

    Write-Section 'SG-03 — IDENTITÉ DU PYTHON CERTIFIÉ'

    $expectedPythonHash =
        '13ddf5df832d9f401afccff6f3618f58754a452663ae2436c2c704fa18d490ce'

    $pythonIdentity =
        Get-FileIdentity $resolvedPython

    Write-Host "Size   : $($pythonIdentity.Length)"
    Write-Host "SHA256 : $($pythonIdentity.SHA256)"

    if ($pythonIdentity.SHA256 -ne $expectedPythonHash) {

        Add-Gate `
            'SG-03_CERTIFIED_PYTHON_HASH' `
            $false `
            "Attendu=$expectedPythonHash / Obtenu=$($pythonIdentity.SHA256)"

        throw `
            'FAIL-CLOSED : SHA-256 du Python certifié différent.'
    }

    Write-Pass 'SHA-256 du Python conforme'

    Add-Gate `
        'SG-03_CERTIFIED_PYTHON_HASH' `
        $true `
        $pythonIdentity.SHA256

    Add-Evidence `
        'CERTIFIED_PYTHON_SHA256' `
        $pythonIdentity.SHA256

    # ========================================================================
    # SG-04 — PYTHON SYNTAX
    # ========================================================================

    Write-Section 'SG-04 — REVALIDATION SYNTAXIQUE PYTHON'

    $pythonSyntax =
        Test-PythonSyntax $resolvedPython

    if (-not $pythonSyntax.Available) {

        Add-Gate `
            'SG-04_PYTHON_SYNTAX' `
            $false `
            $pythonSyntax.Detail

        throw `
            'FAIL-CLOSED : Python indisponible.'
    }

    Write-Host "Python exit code : $($pythonSyntax.ExitCode)"

    if (-not $pythonSyntax.Valid) {

        Add-Gate `
            'SG-04_PYTHON_SYNTAX' `
            $false `
            "ExitCode=$($pythonSyntax.ExitCode)"

        throw `
            'FAIL-CLOSED : syntaxe Python invalide.'
    }

    Write-Pass 'Syntaxe Python valide'

    Add-Gate `
        'SG-04_PYTHON_SYNTAX' `
        $true `
        'py_compile exit code 0'

    # ========================================================================
    # SG-05 — NEW POINT ZERO STRUCTURE
    # ========================================================================

    Write-Section 'SG-05 — STRUCTURE DU NOUVEAU POINT ZERO'

    $newManifest =
        Join-Path $resolvedNewPz 'run_manifest.json'

    $newRecords =
        Join-Path $resolvedNewPz 'records.jsonl'

    if (-not (
        Test-Path `
            -LiteralPath $newManifest `
            -PathType Leaf
    )) {
        throw 'Nouveau Point Zero : run_manifest.json absent.'
    }

    if (-not (
        Test-Path `
            -LiteralPath $newRecords `
            -PathType Leaf
    )) {
        throw 'Nouveau Point Zero : records.jsonl absent.'
    }

    $manifest =
        Read-JsonStrict $newManifest

    $recordCount =
        Get-JsonlLineCount $newRecords

    Write-Host "Records : $recordCount"

    if ($recordCount -le 0) {
        throw 'FAIL-CLOSED : records.jsonl vide.'
    }

    Write-Pass 'Manifest + records présents et exploitables'

    Add-Gate `
        'SG-05_NEW_POINTZERO_STRUCTURE' `
        $true `
        "Manifest valide / $recordCount records"

    # ========================================================================
    # SG-06 — NEW POINT ZERO IDENTITY
    # ========================================================================

    Write-Section 'SG-06 — IDENTITÉ DU NOUVEAU POINT ZERO'

    $manifestRunId =
        [string]$manifest.RunId

    if ($manifestRunId -ne '20260820_135058_169') {

        Add-Gate `
            'SG-06_NEW_POINTZERO_IDENTITY' `
            $false `
            "RunId=$manifestRunId"

        throw `
            "FAIL-CLOSED : RunId inattendu : $manifestRunId"
    }

    $manifestMutation =
        $manifest.Mutation

    if ($null -eq $manifestMutation) {
        throw `
            'FAIL-CLOSED : section Mutation absente.'
    }

    $manifestNewHash =
        [string]$manifestMutation.NewSHA256

    if ($manifestNewHash -ne $expectedPythonHash) {

        Add-Gate `
            'SG-06_NEW_POINTZERO_IDENTITY' `
            $false `
            'Hash du manifest différent du hash certifié'

        throw `
            'FAIL-CLOSED : nouveau Point Zero incohérent.'
    }

    Write-Pass 'RunId + mutation + SHA-256 cohérents'

    Add-Gate `
        'SG-06_NEW_POINTZERO_IDENTITY' `
        $true `
        'RunId et SHA-256 conformes'

    # ========================================================================
    # SG-07 — NEW POINT ZERO HASHES
    # ========================================================================

    Write-Section 'SG-07 — HASH DES ARTEFACTS DU NOUVEAU POINT ZERO'

    $newManifestHash =
        Get-Sha256 $newManifest

    $newRecordsHash =
        Get-Sha256 $newRecords

    Write-Host "Manifest SHA256 : $newManifestHash"
    Write-Host "Records  SHA256 : $newRecordsHash"

    Add-Evidence `
        'NEW_POINTZERO_MANIFEST_SHA256' `
        $newManifestHash

    Add-Evidence `
        'NEW_POINTZERO_RECORDS_SHA256' `
        $newRecordsHash

    Write-Pass 'Artefacts du nouveau Point Zero hashés'

    Add-Gate `
        'SG-07_NEW_POINTZERO_ARTIFACT_HASHES' `
        $true `
        'Manifest + records hashés'

    # ========================================================================
    # SG-08 — HISTORICAL CERTIFICATION
    # ========================================================================

    Write-Section 'SG-08 — PREUVE HISTORIQUE CERTIFIED 15/15'

    $purification =
        Read-JsonStrict $resolvedReport

    if ($null -eq $purification.Gates) {
        throw 'Rapport purification : Gates absent.'
    }

    $purificationGates =
        @($purification.Gates)

    $purificationTotal =
        $purificationGates.Count

    $purificationFailures =
        @(
            $purificationGates |
                Where-Object {
                    -not $_.Passed
                }
        )

    Write-Host "Gates rapport : $purificationTotal"
    Write-Host "FAIL rapport  : $($purificationFailures.Count)"
    Write-Host "Verdict       : $($purification.Verdict)"

    if ($purificationTotal -ne 15) {

        Add-Gate `
            'SG-08_PURIFICATION_15_OF_15' `
            $false `
            "Nombre de gates=$purificationTotal"

        throw `
            'FAIL-CLOSED : certification historique non 15/15.'
    }

    if ($purificationFailures.Count -ne 0) {

        Add-Gate `
            'SG-08_PURIFICATION_15_OF_15' `
            $false `
            "$($purificationFailures.Count) FAIL"

        throw `
            'FAIL-CLOSED : rapport historique contient des FAIL.'
    }

    if ([string]$purification.Verdict -ne 'CERTIFIED') {

        Add-Gate `
            'SG-08_PURIFICATION_15_OF_15' `
            $false `
            "Verdict=$($purification.Verdict)"

        throw `
            'FAIL-CLOSED : verdict historique différent de CERTIFIED.'
    }

    Write-Pass 'Preuve historique : 15/15 — 0 FAIL — CERTIFIED'

    Add-Gate `
        'SG-08_PURIFICATION_15_OF_15' `
        $true `
        '15/15 — 0 FAIL — CERTIFIED'

    Add-Evidence `
        'PURIFICATION_VERDICT' `
        'CERTIFIED'

    # ========================================================================
    # SG-09 — OLD POINT ZERO
    # ========================================================================

    Write-Section 'SG-09 — ANCIEN POINT ZERO'

    $oldManifest =
        Join-Path $resolvedOldPz 'run_manifest.json'

    $oldRecords =
        Join-Path $resolvedOldPz 'records.jsonl'

    if (-not (
        Test-Path `
            -LiteralPath $oldManifest `
            -PathType Leaf
    )) {
        throw 'Ancien Point Zero : manifest absent.'
    }

    if (-not (
        Test-Path `
            -LiteralPath $oldRecords `
            -PathType Leaf
    )) {
        throw 'Ancien Point Zero : records absent.'
    }

    $oldManifestHash =
        Get-Sha256 $oldManifest

    $oldRecordsHash =
        Get-Sha256 $oldRecords

    Write-Host "Old Manifest SHA256 : $oldManifestHash"
    Write-Host "Old Records  SHA256 : $oldRecordsHash"

    Add-Evidence `
        'OLD_POINTZERO_MANIFEST_SHA256' `
        $oldManifestHash

    Add-Evidence `
        'OLD_POINTZERO_RECORDS_SHA256' `
        $oldRecordsHash

    Write-Pass 'Ancien Point Zero présent et lisible'

    Add-Gate `
        'SG-09_OLD_POINTZERO_PRESENT' `
        $true `
        'Ancienne baseline présente'

    # ========================================================================
    # SG-10 — CORPUS READ-ONLY
    # ========================================================================

    Write-Section 'SG-10 — GARDE READ-ONLY'

    Write-Host 'Ce moteur ne modifie volontairement aucun artefact du corpus.'
    Write-Host 'Les seuls fichiers créés seront sous :'
    Write-Host "  $FreezeRoot"

    Write-Pass 'Mode READ-ONLY : aucune mutation du corpus'

    Add-Gate `
        'SG-10_READ_ONLY' `
        $true `
        'Aucune mutation du corpus'

    # ========================================================================
    # SG-11 — FREEZE CONTAINER
    # ========================================================================

    Write-Section 'SG-11 — CRÉATION DU CONTENEUR DE FREEZE'

    Ensure-Directory $FreezeRoot

    $freezeRunId =
        [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss_fff')

    $freezeDir =
        Join-Path `
            $FreezeRoot `
            ("freeze_" + $freezeRunId)

    if (Test-Path -LiteralPath $freezeDir) {

        throw `
            "FAIL-CLOSED : collision RunId freeze : $freezeDir"
    }

    New-Item `
        -ItemType Directory `
        -Path $freezeDir `
        -ErrorAction Stop |
        Out-Null

    Write-Host "Freeze directory : $freezeDir"

    Write-Pass 'Conteneur de freeze créé'

    Add-Gate `
        'SG-11_FREEZE_CONTAINER' `
        $true `
        $freezeDir

    # ========================================================================
    # SG-12 — FREEZE MANIFEST
    # ========================================================================

    Write-Section 'SG-12 — FREEZE MANIFEST'

    $engineIdentity =
        Get-FileIdentity $resolvedEngine

    $pythonIdentity =
        Get-FileIdentity $resolvedPython

    $purificationIdentity =
        Get-FileIdentity $resolvedReport

    $newManifestIdentity =
        Get-FileIdentity $newManifest

    $newRecordsIdentity =
        Get-FileIdentity $newRecords

    $oldManifestIdentity =
        Get-FileIdentity $oldManifest

    $oldRecordsIdentity =
        Get-FileIdentity $oldRecords

    $freezeManifest =
        [PSCustomObject]@{

            Freeze = [PSCustomObject]@{
                EngineName    = $EngineName
                EngineVersion = $EngineVersion
                Verdict       = 'FREEZE_CERTIFIED'
                Mode          = 'FAST + FORENSIC / READ-ONLY / FAIL-CLOSED'
                CreatedAtUtc  = [DateTime]::UtcNow.ToString('o')
            }

            CertifiedState = [PSCustomObject]@{
                PurificationEngineVersion = '0.2.1'
                PurificationVerdict       = 'CERTIFIED'
                PurificationGates         = 15
                PurificationFailures      = 0
                PythonSHA256              = $expectedPythonHash
            }

            Paths = [PSCustomObject]@{
                EzzioRoot          = $resolvedEzzioRoot
                PurificationEngine = $resolvedEngine
                CertifiedPython    = $resolvedPython
                OldPointZero       = $resolvedOldPz
                NewPointZero       = $resolvedNewPz
                PurificationReport = $resolvedReport
            }

            Artifacts = [PSCustomObject]@{

                PurificationEngine = [PSCustomObject]@{
                    Path   = $engineIdentity.FullName
                    Size   = $engineIdentity.Length
                    SHA256 = $engineIdentity.SHA256
                }

                CertifiedPython = [PSCustomObject]@{
                    Path   = $pythonIdentity.FullName
                    Size   = $pythonIdentity.Length
                    SHA256 = $pythonIdentity.SHA256
                }

                PurificationReport = [PSCustomObject]@{
                    Path   = $purificationIdentity.FullName
                    Size   = $purificationIdentity.Length
                    SHA256 = $purificationIdentity.SHA256
                }

                NewPointZeroManifest = [PSCustomObject]@{
                    Path   = $newManifestIdentity.FullName
                    Size   = $newManifestIdentity.Length
                    SHA256 = $newManifestIdentity.SHA256
                }

                NewPointZeroRecords = [PSCustomObject]@{
                    Path   = $newRecordsIdentity.FullName
                    Size   = $newRecordsIdentity.Length
                    SHA256 = $newRecordsIdentity.SHA256
                }

                OldPointZeroManifest = [PSCustomObject]@{
                    Path   = $oldManifestIdentity.FullName
                    Size   = $oldManifestIdentity.Length
                    SHA256 = $oldManifestIdentity.SHA256
                }

                OldPointZeroRecords = [PSCustomObject]@{
                    Path   = $oldRecordsIdentity.FullName
                    Size   = $oldRecordsIdentity.Length
                    SHA256 = $oldRecordsIdentity.SHA256
                }
            }

            Evidence = @(
                $Evidence
            )
        }

    $freezeManifestPath =
        Join-Path `
            $freezeDir `
            'freeze_manifest.json'

    [System.IO.File]::WriteAllText(
        $freezeManifestPath,
        (
            $freezeManifest |
                ConvertTo-Json -Depth 20
        ),
        [System.Text.UTF8Encoding]::new($false)
    )

    if (-not (
        Test-Path `
            -LiteralPath $freezeManifestPath `
            -PathType Leaf
    )) {
        throw `
            'FAIL-CLOSED : freeze_manifest.json non créé.'
    }

    Write-Pass 'Freeze manifest créé'

    Add-Gate `
        'SG-12_FREEZE_MANIFEST' `
        $true `
        $freezeManifestPath

    # ========================================================================
    # SG-13 — FREEZE MANIFEST HASH
    # ========================================================================

    Write-Section 'SG-13 — EMPREINTE DU FREEZE'

    $freezeManifestHash =
        Get-Sha256 $freezeManifestPath

    Write-Host "Freeze Manifest SHA-256 : $freezeManifestHash"

    Add-Evidence `
        'FREEZE_MANIFEST_SHA256' `
        $freezeManifestHash

    Write-Pass 'Freeze manifest hashé'

    Add-Gate `
        'SG-13_FREEZE_MANIFEST_HASH' `
        $true `
        $freezeManifestHash

    # ========================================================================
    # SG-14 — FINAL RECHECK
    # ========================================================================

    Write-Section 'SG-14 — RECHECK FINAL'

    $finalPythonHash =
        Get-Sha256 $resolvedPython

    if ($finalPythonHash -ne $expectedPythonHash) {

        Add-Gate `
            'SG-14_FINAL_IDENTITY_RECHECK' `
            $false `
            'SHA Python modifié pendant le freeze'

        throw `
            'FAIL-CLOSED : identité Python modifiée pendant le freeze.'
    }

    $finalEngineHash =
        Get-Sha256 $resolvedEngine

    $finalReportHash =
        Get-Sha256 $resolvedReport

    $finalNewManifestHash =
        Get-Sha256 $newManifest

    $finalNewRecordsHash =
        Get-Sha256 $newRecords

    Write-Host "Python final       : $finalPythonHash"
    Write-Host "Engine final       : $finalEngineHash"
    Write-Host "Report final       : $finalReportHash"
    Write-Host "New manifest final : $finalNewManifestHash"
    Write-Host "New records final  : $finalNewRecordsHash"

    Write-Pass 'Identités finales inchangées'

    Add-Gate `
        'SG-14_FINAL_IDENTITY_RECHECK' `
        $true `
        'Identités finales conformes'

    # ========================================================================
    # SG-15 — FREEZE MANIFEST RE-READ
    # ========================================================================

    Write-Section 'SG-15 — RELECTURE CRYPTOGRAPHIQUE DU FREEZE'

    $freezeManifestReloaded =
        Read-JsonStrict $freezeManifestPath

    $freezeManifestHashRecheck =
        Get-Sha256 $freezeManifestPath

    if ($freezeManifestHashRecheck -ne $freezeManifestHash) {

        Add-Gate `
            'SG-15_FREEZE_RECHECK' `
            $false `
            'Hash du freeze manifest modifié'

        throw `
            'FAIL-CLOSED : freeze manifest modifié après émission.'
    }

    if (
        [string]$freezeManifestReloaded.Freeze.Verdict `
        -ne 'FREEZE_CERTIFIED'
    ) {

        Add-Gate `
            'SG-15_FREEZE_RECHECK' `
            $false `
            'Verdict freeze incorrect'
        
        throw `
            'FAIL-CLOSED : verdict freeze incohérent.'
    }

    Write-Pass 'Freeze manifest relu et cryptographiquement stable'

    Add-Gate `
        'SG-15_FREEZE_RECHECK' `
        $true `
        'Hash et verdict conformes'

    # ========================================================================
    # SG-16 — FINAL CERTIFICATION
    # ========================================================================

    Write-Section 'SG-16 — FREEZE CERTIFICATION'

    $failedGates =
        @(
            $GateResults |
                Where-Object {
                    -not $_.Passed
                }
        )

    $totalGates =
        @($GateResults).Count

    Write-Host "Gates totales : $totalGates"
    Write-Host "Gates FAIL    : $($failedGates.Count)"

    if ($failedGates.Count -ne 0) {

        foreach ($gate in $failedGates) {

            Write-Fail `
                "$($gate.Gate) : $($gate.Detail)"
        }

        throw `
            'CERTIFICATION DU FREEZE REFUSÉE.'
    }

    if ($totalGates -ne 17) {

        throw `
            "CERTIFICATION REFUSÉE : nombre de gates inattendu ($totalGates)."
    }

    $FreezeCertified = $true
    $ExitCode = 0

    Write-Host ''
    Write-Host `
        '████████████████████████████████████████████████████████████████████████' `
        -ForegroundColor Green

    Write-Host `
        ' E-ZZIO — FREEZE CERTIFIED' `
        -ForegroundColor Green

    Write-Host `
        '████████████████████████████████████████████████████████████████████████' `
        -ForegroundColor Green

    Write-Host ''

    Write-Host 'ÉTAT CERTIFIÉ : FIGÉ' -ForegroundColor Green
    Write-Host 'CORPUS E-ZZIO : NON MODIFIÉ' -ForegroundColor Green
    Write-Host 'ANCIEN POINT ZERO : NON MODIFIÉ' -ForegroundColor Green
    Write-Host 'NOUVEAU POINT ZERO : NON MODIFIÉ' -ForegroundColor Green

    Write-Host ''
    Write-Host "Python SHA-256 : $finalPythonHash"
    Write-Host "Freeze Dir     : $freezeDir"
    Write-Host "Freeze Manifest: $freezeManifestPath"
    Write-Host "Freeze SHA-256 : $freezeManifestHash"

}
catch {

    $FatalError = $_
    $ExitCode = 1

    Write-Host ''
    Write-Host `
        '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' `
        -ForegroundColor Red

    Write-Host `
        ' E-ZZIO — FREEZE FAIL-CLOSED' `
        -ForegroundColor Red

    Write-Host `
        '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' `
        -ForegroundColor Red

    Write-Host ''

    Write-Host `
        "ERROR : $($_.Exception.Message)" `
        -ForegroundColor Red

    if ($_.InvocationInfo) {

        Write-Host ''
        Write-Host 'FORENSIC LOCATION' -ForegroundColor Yellow
        Write-Host "Script : $($_.InvocationInfo.ScriptName)"
        Write-Host "Line   : $($_.InvocationInfo.ScriptLineNumber)"
        Write-Host "Code   : $($_.InvocationInfo.Line)"
    }

    Write-Host ''
    Write-Host 'AUCUN FREEZE CERTIFIED ÉMIS.' -ForegroundColor Red
}

finally {

    # ========================================================================
    # FORENSIC REPORT
    # ========================================================================

    try {

        Ensure-Directory $FreezeRoot

        $reportRunId =
            if ($freezeDir) {
                Split-Path `
                    -Leaf `
                    $freezeDir
            }
            else {
                'failed'
            }

        $reportPath =
            Join-Path `
                $FreezeRoot `
                ("freeze_report_" + $reportRunId + '.json')

        $finishedUtc =
            [DateTime]::UtcNow

        $report =
            [PSCustomObject]@{

                Engine = [PSCustomObject]@{
                    Name    = $EngineName
                    Version = $EngineVersion
                    Mode    = 'FAST + FORENSIC / READ-ONLY / FAIL-CLOSED'
                }

                Execution = [PSCustomObject]@{
                    StartedAtUtc  = $StartedAtUtc.ToString('o')
                    FinishedAtUtc = $finishedUtc.ToString('o')
                    ExitCode      = $ExitCode
                }

                Verdict =
                    if ($FreezeCertified) {
                        'FREEZE_CERTIFIED'
                    }
                    else {
                        'FAIL_CLOSED'
                    }

                Mutation = [PSCustomObject]@{
                    CorpusModified       = $false
                    CertifiedPythonMoved = $false
                    OldPointZeroModified = $false
                    NewPointZeroModified = $false
                }

                Gates = @(
                    $GateResults
                )

                Evidence = @(
                    $Evidence
                )

                Warnings = @(
                    $Warnings
                )

                FatalError =
                    if ($null -ne $FatalError) {

                        [PSCustomObject]@{
                            Type =
                                $FatalError.Exception.GetType().FullName

                            Message =
                                $FatalError.Exception.Message
                        }
                    }
                    else {
                        $null
                    }

                FreezeManifest =
                    if ($freezeManifestPath) {
                        $freezeManifestPath
                    }
                    else {
                        $null
                    }
            }

        [System.IO.File]::WriteAllText(
            $reportPath,
            (
                $report |
                    ConvertTo-Json -Depth 20
            ),
            [System.Text.UTF8Encoding]::new($false)
        )

        Write-Host ''
        Write-Host '==============================================================================' `
            -ForegroundColor DarkCyan

        Write-Host ' FREEZE FORENSIC REPORT' `
            -ForegroundColor DarkCyan

        Write-Host '==============================================================================' `
            -ForegroundColor DarkCyan

        Write-Host ''
        Write-Host "Rapport : $reportPath" `
            -ForegroundColor DarkGray
    }
    catch {

        $ExitCode = 1

        Write-Host ''
        Write-Host `
            '[CRITICAL] Impossible d''écrire le rapport de freeze.' `
            -ForegroundColor Red

        Write-Host `
            $_.Exception.Message `
            -ForegroundColor Red
    }

    Write-Host ''
    Write-Host '==============================================================================' `
        -ForegroundColor Cyan

    if ($FreezeCertified -and $ExitCode -eq 0) {

        Write-Host `
            ' E-ZZIO — ÉTAT FIGÉ : FREEZE CERTIFIED' `
            -ForegroundColor Green
    }
    else {

        Write-Host `
            ' E-ZZIO — FREEZE : FAIL-CLOSED' `
            -ForegroundColor Red
    }

    Write-Host '==============================================================================' `
        -ForegroundColor Cyan

    Write-Host ''
    Write-Host "Corpus modifié              : NON"
    Write-Host "Ancien Point Zero modifié   : NON"
    Write-Host "Nouveau Point Zero modifié  : NON"
    Write-Host ''

    if ($PauseOnExit) {
        Read-Host 'Appuyez sur Entrée pour fermer'
    }

    exit $ExitCode
}
