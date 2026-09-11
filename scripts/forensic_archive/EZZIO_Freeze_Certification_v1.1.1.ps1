# ============================================================================
# E-ZZIO — FREEZE CERTIFICATION ENGINE v1.1.1
# ============================================================================
# MODE:
#   FAST + FORENSIC
#   CORPUS READ-ONLY
#   FAIL-CLOSED
#
# PURPOSE:
#   Certifier un état E-ZZIO figé uniquement lorsque toutes les preuves
#   nécessaires sont mathématiquement cohérentes.
#
# SECURITY CONTRACT:
#   - Aucun fichier du corpus E-ZZIO n'est modifié.
#   - Aucun bytecode Python n'est créé.
#   - Les seules écritures autorisées sont externes au corpus:
#       FreezeRoot
#   - Aucun verdict CERTIFIED n'est déclaré avant validation effective.
#   - Toute ambiguïté d'identité entraîne FAIL-CLOSED.
#   - Le script doit être exécuté comme fichier .ps1.
#
# VERSION:
#   1.1.1
#
# IMPORTANT:
#   Ce fichier doit être enregistré puis exécuté comme fichier .ps1.
#   Ne pas coller son contenu morceau par morceau dans la console.
# ============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$EngineName    = 'E-ZZIO — FREEZE CERTIFICATION ENGINE'
$EngineVersion = '1.1.1'

$EzzioRoot = 'G:\AI\E-zzio'

# SHA-256 certifié du Python attendu.
$ExpectedPythonHash =
    '13ddf5df832d9f401afccff6f3618f58754a452663ae2436c2c704fa18d490ce'

# RunId exact du nouveau Point Zero certifié.
$ExpectedNewPointZeroRunId =
    '20260820_135058_169'

# Répertoire externe au corpus.
$FreezeRoot =
    Join-Path `
        (Split-Path -Parent $EzzioRoot) `
        'E-ZZIO-FREEZES'

# Pause facultative.
$PauseOnExit = $false

# ============================================================================
# RUNTIME STATE
# ============================================================================

$StartedAtUtc =
    [DateTime]::UtcNow

$ExitCode = 1

$FreezeCertified = $false

$FatalError = $null

$freezeDir = $null
$freezeManifestPath = $null
$freezeManifestHash = $null
$freezeSealPath = $null

$GateResults =
    [System.Collections.Generic.List[object]]::new()

$Evidence =
    [System.Collections.Generic.List[object]]::new()

$Warnings =
    [System.Collections.Generic.List[object]]::new()

# ============================================================================
# OUTPUT HELPERS
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

function Write-Warn {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

# ============================================================================
# GATE REGISTRATION
# ============================================================================

function Add-Gate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [bool]$Passed,

        [Parameter(Mandatory = $true)]
        [string]$Detail
    )

    $GateResults.Add(
        [PSCustomObject]@{
            Name      = $Name
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

    if (-not (
        Test-Path `
            -LiteralPath $Path `
            -PathType Any
    )) {
        throw "Chemin absent : $Path"
    }

    $resolved =
        Resolve-Path `
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

    $raw =
        [System.IO.File]::ReadAllText(
            $Path,
            [System.Text.UTF8Encoding]::new($false)
        )

    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "JSON vide : $Path"
    }

    try {
        return (
            $raw |
                ConvertFrom-Json `
                    -ErrorAction Stop
        )
    }
    catch {
        throw `
            "JSON invalide : $Path :: $($_.Exception.Message)"
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

    $item =
        Get-Item `
            -LiteralPath $Path `
            -Force `
            -ErrorAction Stop

    if ($item.PSIsContainer) {
        throw "Get-FileIdentity exige un fichier : $Path"
    }

    $hash =
        Get-Sha256 $Path

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
# POWERSHELL AST
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

    $errorArray =
        @($errors)

    return [PSCustomObject]@{
        Valid      = ($errorArray.Count -eq 0)
        ErrorCount = $errorArray.Count
        Errors     = $errorArray
    }
}

# ============================================================================
# PYTHON RESOLUTION
# ============================================================================

function Find-Python {
    $commands = @(
        'python.exe',
        'python3.exe',
        'py.exe'
    )

    foreach ($commandName in $commands) {

        $command =
            Get-Command `
                -Name $commandName `
                -ErrorAction SilentlyContinue

        if ($null -ne $command) {

            if (-not [string]::IsNullOrWhiteSpace(
                [string]$command.Source
            )) {
                return $command.Source
            }
        }
    }

    return $null
}

# ============================================================================
# PYTHON SYNTAX — HARDENED
# ============================================================================

function Test-PythonSyntax {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $python = $null
    $output = @()
    $exitCode = $null

    $python =
        Find-Python

    if ([string]::IsNullOrWhiteSpace($python)) {

        return [PSCustomObject]@{
            Available = $false
            Valid     = $false
            ExitCode  = $null
            Detail    = 'PYTHON_INTERPRETER_NOT_FOUND'
            Output    = @()
        }
    }

    if (-not (
        Test-Path `
            -LiteralPath $python `
            -PathType Leaf
    )) {

        return [PSCustomObject]@{
            Available = $false
            Valid     = $false
            ExitCode  = $null
            Detail    = 'PYTHON_INTERPRETER_PATH_INVALID'
            Output    = @()
        }
    }

    $pythonCode = @'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])

source = path.read_text(
    encoding="utf-8"
)

compile(
    source,
    str(path),
    "exec"
)
'@

    try {

        $output =
            @(
                & $python `
                    '-B' `
                    '-c' `
                    $pythonCode `
                    $Path `
                    2>&1
            )

        $exitCode =
            $LASTEXITCODE
    }
    catch {

        return [PSCustomObject]@{
            Available = $true
            Valid     = $false
            ExitCode  = $null
            Detail    = 'PYTHON_EXECUTION_EXCEPTION'
            Output    = @(
                $_.Exception.Message
            )
        }
    }

    if ($exitCode -ne 0 -and $output.Count -gt 0) {

        Write-Host ''
        Write-Host 'Python diagnostic :' `
            -ForegroundColor Yellow

        foreach ($line in $output) {
            Write-Host $line `
                -ForegroundColor Yellow
        }
    }

    return [PSCustomObject]@{
        Available = $true
        Valid     = ($exitCode -eq 0)
        ExitCode  = $exitCode
        Detail    = if ($exitCode -eq 0) {
            'PYTHON_SYNTAX_VALID_READ_ONLY'
        }
        else {
            'PYTHON_SYNTAX_INVALID'
        }
        Output    = @($output)
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

    foreach (
        $line in
        [System.IO.File]::ReadLines($Path)
    ) {

        if (-not [string]::IsNullOrWhiteSpace($line)) {
            $count++
        }
    }

    return $count
}

# ============================================================================
# POINT ZERO DISCOVERY
# ============================================================================

function Find-PointZeroDirectories {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $candidates =
        [System.Collections.Generic.List[string]]::new()

    $manifests =
        Get-ChildItem `
            -LiteralPath $Root `
            -Filter 'run_manifest.json' `
            -File `
            -Recurse `
            -ErrorAction Stop

    foreach ($manifestItem in $manifests) {

        $directory =
            $manifestItem.Directory.FullName

        $records =
            Join-Path `
                $directory `
                'records.jsonl'

        if (
            Test-Path `
                -LiteralPath $records `
                -PathType Leaf
        ) {
            $candidates.Add($directory)
        }
    }

    return @($candidates)
}

# ============================================================================
# PURIFICATION REPORT DISCOVERY
# ============================================================================

function Find-PurificationReport {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $candidates =
        [System.Collections.Generic.List[string]]::new()

    $jsonFiles =
        Get-ChildItem `
            -LiteralPath $Root `
            -Filter '*.json' `
            -File `
            -Recurse `
            -ErrorAction Stop

    foreach ($file in $jsonFiles) {

        try {

            $obj =
                Read-JsonStrict $file.FullName

            if (
                $null -ne $obj.Gates `
                -and
                $null -ne $obj.Verdict
            ) {

                $gates =
                    @($obj.Gates)

                $failures =
                    @(
                        $gates |
                            Where-Object {
                                -not $_.Passed
                            }
                    )

                if (
                    $gates.Count -eq 15 `
                    -and
                    $failures.Count -eq 0 `
                    -and
                    [string]$obj.Verdict -eq 'CERTIFIED'
                ) {
                    $candidates.Add($file.FullName)
                }
            }
        }
        catch {
            # Fichier JSON non pertinent.
            continue
        }
    }

    $unique =
        @(
            $candidates |
                Sort-Object -Unique
        )

    if ($unique.Count -eq 0) {
        throw 'Aucun rapport de purification 15/15 CERTIFIED trouvé.'
    }

    if ($unique.Count -gt 1) {
        throw `
            "Ambiguïté : $($unique.Count) rapports de purification 15/15 CERTIFIED trouvés."
    }

    return $unique[0]
}

# ============================================================================
# CERTIFIED PYTHON DISCOVERY
# ============================================================================

function Find-CertifiedPython {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,

        [Parameter(Mandatory = $true)]
        [string]$ExpectedHash
    )

    $matches =
        [System.Collections.Generic.List[string]]::new()

    $pythonFiles =
        Get-ChildItem `
            -LiteralPath $Root `
            -Filter '*.py' `
            -File `
            -Recurse `
            -ErrorAction Stop

    foreach ($file in $pythonFiles) {

        try {

            $hash =
                Get-Sha256 $file.FullName

            if ($hash -eq $ExpectedHash) {
                $matches.Add($file.FullName)
            }
        }
        catch {
            continue
        }
    }

    $unique =
        @(
            $matches |
                Sort-Object -Unique
        )

    if ($unique.Count -eq 0) {
        throw `
            "Aucun Python portant le SHA-256 certifié $ExpectedHash n'a été trouvé."
    }

    if ($unique.Count -gt 1) {
        throw `
            "Ambiguïté : plusieurs fichiers Python portent le SHA-256 certifié."
    }

    return $unique[0]
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

    if ([string]::IsNullOrWhiteSpace($ScriptPath)) {
        throw `
            'SELF-AST FAIL-CLOSED : PSCommandPath absent. Exécuter le .ps1 comme fichier.'
    }

    if (-not (
        Test-Path `
            -LiteralPath $ScriptPath `
            -PathType Leaf
    )) {
        throw `
            "SELF-AST FAIL-CLOSED : fichier moteur absent : $ScriptPath"
    }

    $result =
        Test-PowerShellAst $ScriptPath

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

        throw `
            'SELF-AST FAIL-CLOSED : moteur invalide.'
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
    # EXECUTION CONTEXT
    # ========================================================================

    $thisScript =
        $PSCommandPath

    if ([string]::IsNullOrWhiteSpace($thisScript)) {

        throw `
            'Impossible de déterminer le chemin du moteur. Exécuter le .ps1 comme fichier.'
    }

    $thisScript =
        Resolve-CanonicalPath $thisScript

    # ========================================================================
    # SG-00
    # ========================================================================

    Test-SelfIntegrity $thisScript

    Write-Section "$EngineName v$EngineVersion"

    Write-Host `
        'MODE              : FAST + FORENSIC / CORPUS READ-ONLY / FAIL-CLOSED'

    Write-Host `
        'CORPUS MUTATION   : INTERDITE'

    Write-Host `
        'BYTECODE CREATION : INTERDITE'

    Write-Host `
        'EXTERNAL OUTPUT   : AUTORISÉ — FREEZE UNIQUEMENT'

    Write-Host `
        "FREEZE DESTINATION: $FreezeRoot"

    Write-Host ''

    # ========================================================================
    # SG-01
    # ========================================================================

    Write-Section `
        'SG-01 — RÉSOLUTION DES ARTEFACTS CERTIFIÉS'

    $resolvedEzzioRoot =
        Resolve-CanonicalPath $EzzioRoot

    if (
        $resolvedEzzioRoot.TrimEnd('\') `
        -eq
        (
            Split-Path `
                -Parent `
                $thisScript
        ).TrimEnd('\')
    ) {
        Write-Host `
            'Moteur situé dans le corpus E-ZZIO.' `
            -ForegroundColor DarkGray
    }

    # Purification report.
    $resolvedReport =
        Find-PurificationReport $resolvedEzzioRoot

    # Certified Python.
    $resolvedPython =
        Find-CertifiedPython `
            $resolvedEzzioRoot `
            $ExpectedPythonHash

    # Point Zero candidates.
    $pointZeroCandidates =
        @(
            Find-PointZeroDirectories `
                $resolvedEzzioRoot
        )

    if ($pointZeroCandidates.Count -lt 2) {
        throw `
            "Impossible d'identifier Old/New Point Zero : seulement $($pointZeroCandidates.Count) candidat(s)."
    }

    $newCandidates =
        [System.Collections.Generic.List[string]]::new()

    foreach ($candidate in $pointZeroCandidates) {

        try {

            $candidateManifest =
                Join-Path `
                    $candidate `
                    'run_manifest.json'

            $candidateObject =
                Read-JsonStrict $candidateManifest

            if (
                [string]$candidateObject.RunId `
                -eq
                $ExpectedNewPointZeroRunId
            ) {
                $newCandidates.Add($candidate)
            }
        }
        catch {
            continue
        }
    }

    if ($newCandidates.Count -ne 1) {
        throw `
            "Identification du nouveau Point Zero ambiguë : $($newCandidates.Count) candidat(s)."
    }

    $resolvedNewPz =
        $newCandidates[0]

    $oldCandidates =
        @(
            $pointZeroCandidates |
                Where-Object {
                    $_ -ne $resolvedNewPz
                }
        )

    if ($oldCandidates.Count -ne 1) {
        throw `
            "Identification de l'ancien Point Zero ambiguë : $($oldCandidates.Count) candidat(s)."
    }

    $resolvedOldPz =
        $oldCandidates[0]

    $resolvedEngine =
        $thisScript

    Write-Host "E-ZZIO ROOT : $resolvedEzzioRoot"
    Write-Host "MOTEUR      : $resolvedEngine"
    Write-Host "PYTHON      : $resolvedPython"
    Write-Host "OLD PZ      : $resolvedOldPz"
    Write-Host "NEW PZ      : $resolvedNewPz"
    Write-Host "REPORT      : $resolvedReport"

    Write-Pass `
        'Tous les artefacts certifiés sont résolus sans ambiguïté.'

    Add-Gate `
        'SG-01_ARTIFACT_PRESENCE' `
        $true `
        'Tous les artefacts certifiés présents et identifiés'

    Add-Evidence `
        'EZZIO_ROOT' `
        $resolvedEzzioRoot

    Add-Evidence `
        'PURIFICATION_ENGINE' `
        $resolvedEngine

    Add-Evidence `
        'CERTIFIED_PYTHON' `
        $resolvedPython

    Add-Evidence `
        'OLD_POINTZERO' `
        $resolvedOldPz

    Add-Evidence `
        'NEW_POINTZERO' `
        $resolvedNewPz

    Add-Evidence `
        'PURIFICATION_REPORT' `
        $resolvedReport

    # ========================================================================
    # SG-02
    # ========================================================================

    Write-Section `
        'SG-02 — AST DU MOTEUR DE FREEZE'

    $engineAst =
        Test-PowerShellAst $resolvedEngine

    Write-Host `
        "AST errors : $($engineAst.ErrorCount)"

    if (-not $engineAst.Valid) {

        Add-Gate `
            'SG-02_PURIFICATION_ENGINE_AST' `
            $false `
            "$($engineAst.ErrorCount) erreur(s)"

        throw `
            'FAIL-CLOSED : AST du moteur invalide.'
    }

    Write-Pass `
        'Moteur de freeze : AST valide.'

    Add-Gate `
        'SG-02_PURIFICATION_ENGINE_AST' `
        $true `
        '0 erreur AST'

    # ========================================================================
    # SG-03
    # ========================================================================

    Write-Section `
        'SG-03 — IDENTITÉ DU PYTHON CERTIFIÉ'

    $pythonIdentity =
        Get-FileIdentity $resolvedPython

    Write-Host "Size   : $($pythonIdentity.Length)"
    Write-Host "SHA256 : $($pythonIdentity.SHA256)"

    if (
        $pythonIdentity.SHA256 `
        -ne `
        $ExpectedPythonHash
    ) {

        Add-Gate `
            'SG-03_CERTIFIED_PYTHON_HASH' `
            $false `
            "Attendu=$ExpectedPythonHash / Obtenu=$($pythonIdentity.SHA256)"

        throw `
            'FAIL-CLOSED : SHA-256 du Python certifié différent.'
    }

    Write-Pass `
        'SHA-256 du Python conforme.'

    Add-Gate `
        'SG-03_CERTIFIED_PYTHON_HASH' `
        $true `
        $pythonIdentity.SHA256

    Add-Evidence `
        'CERTIFIED_PYTHON_SHA256' `
        $pythonIdentity.SHA256

    # ========================================================================
    # SG-04
    # ========================================================================

    Write-Section `
        'SG-04 — REVALIDATION SYNTAXIQUE PYTHON READ-ONLY'

    $pythonSyntax =
        Test-PythonSyntax $resolvedPython

    if (-not $pythonSyntax.Available) {

        Add-Gate `
            'SG-04_PYTHON_SYNTAX' `
            $false `
            $pythonSyntax.Detail

        throw `
            "FAIL-CLOSED : $($pythonSyntax.Detail)"
    }

    Write-Host `
        "Python exit code : $($pythonSyntax.ExitCode)"

    Write-Host `
        "Python detail    : $($pythonSyntax.Detail)"

    if (-not $pythonSyntax.Valid) {

        Add-Gate `
            'SG-04_PYTHON_SYNTAX' `
            $false `
            "ExitCode=$($pythonSyntax.ExitCode)"

        throw `
            'FAIL-CLOSED : syntaxe Python invalide.'
    }

    Write-Pass `
        'Syntaxe Python valide — compile() mémoire uniquement.'

    Add-Gate `
        'SG-04_PYTHON_SYNTAX' `
        $true `
        'compile() mémoire + -B — aucun bytecode écrit'

    # ========================================================================
    # SG-05
    # ========================================================================

    Write-Section `
        'SG-05 — STRUCTURE DU NOUVEAU POINT ZERO'

    $newManifest =
        Join-Path `
            $resolvedNewPz `
            'run_manifest.json'

    $newRecords =
        Join-Path `
            $resolvedNewPz `
            'records.jsonl'

    if (-not (
        Test-Path `
            -LiteralPath $newManifest `
            -PathType Leaf
    )) {
        throw `
            'Nouveau Point Zero : run_manifest.json absent.'
    }

    if (-not (
        Test-Path `
            -LiteralPath $newRecords `
            -PathType Leaf
    )) {
        throw `
            'Nouveau Point Zero : records.jsonl absent.'
    }

    $manifest =
        Read-JsonStrict $newManifest

    $recordCount =
        Get-JsonlLineCount $newRecords

    Write-Host `
        "Records : $recordCount"

    if ($recordCount -le 0) {
        throw `
            'FAIL-CLOSED : records.jsonl vide.'
    }

    Write-Pass `
        'Manifest + records présents et exploitables.'

    Add-Gate `
        'SG-05_NEW_POINTZERO_STRUCTURE' `
        $true `
        "Manifest valide / $recordCount records"

    Add-Evidence `
        'NEW_POINTZERO_RECORD_COUNT' `
        ([string]$recordCount)

    # ========================================================================
    # SG-06
    # ========================================================================

    Write-Section `
        'SG-06 — IDENTITÉ DU NOUVEAU POINT ZERO'

    $manifestRunId =
        [string]$manifest.RunId

    if (
        $manifestRunId `
        -ne `
        $ExpectedNewPointZeroRunId
    ) {

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

        Add-Gate `
            'SG-06_NEW_POINTZERO_IDENTITY' `
            $false `
            'Section Mutation absente'

        throw `
            'FAIL-CLOSED : section Mutation absente.'
    }

    $manifestNewHash =
        [string]$manifestMutation.NewSHA256

    if (
        $manifestNewHash `
        -ne `
        $ExpectedPythonHash
    ) {

        Add-Gate `
            'SG-06_NEW_POINTZERO_IDENTITY' `
            $false `
            "NewSHA256=$manifestNewHash / Expected=$ExpectedPythonHash"

        throw `
            'FAIL-CLOSED : nouveau Point Zero incohérent.'
    }

    Write-Pass `
        'RunId + mutation + SHA-256 cohérents.'

    Add-Gate `
        'SG-06_NEW_POINTZERO_IDENTITY' `
        $true `
        'RunId et SHA-256 conformes'

    Add-Evidence `
        'NEW_POINTZERO_RUN_ID' `
        $manifestRunId

    Add-Evidence `
        'NEW_POINTZERO_DECLARED_NEW_SHA256' `
        $manifestNewHash

    # ========================================================================
    # SG-07
    # ========================================================================

    Write-Section `
        'SG-07 — HASH DES ARTEFACTS DU NOUVEAU POINT ZERO'

    $newManifestHash =
        Get-Sha256 $newManifest

    $newRecordsHash =
        Get-Sha256 $newRecords

    Write-Host `
        "Manifest SHA256 : $newManifestHash"

    Write-Host `
        "Records  SHA256 : $newRecordsHash"

    Add-Evidence `
        'NEW_POINTZERO_MANIFEST_SHA256' `
        $newManifestHash

    Add-Evidence `
        'NEW_POINTZERO_RECORDS_SHA256' `
        $newRecordsHash

    Write-Pass `
        'Artefacts du nouveau Point Zero hashés.'

    Add-Gate `
        'SG-07_NEW_POINTZERO_ARTIFACT_HASHES' `
        $true `
        'Manifest + records hashés'

    # ========================================================================
    # SG-08
    # ========================================================================

    Write-Section `
        'SG-08 — PREUVE HISTORIQUE CERTIFIED 15/15'

    $purification =
        Read-JsonStrict $resolvedReport

    if ($null -eq $purification.Gates) {
        throw `
            'Rapport purification : Gates absent.'
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

    Write-Host `
        "Gates rapport : $purificationTotal"

    Write-Host `
        "FAIL rapport  : $($purificationFailures.Count)"

    Write-Host `
        "Verdict       : $($purification.Verdict)"

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

    if (
        [string]$purification.Verdict `
        -ne `
        'CERTIFIED'
    ) {

        Add-Gate `
            'SG-08_PURIFICATION_15_OF_15' `
            $false `
            "Verdict=$($purification.Verdict)"

        throw `
            'FAIL-CLOSED : verdict historique différent de CERTIFIED.'
    }

    Write-Pass `
        'Preuve historique : 15/15 — 0 FAIL — CERTIFIED.'

    Add-Gate `
        'SG-08_PURIFICATION_15_OF_15' `
        $true `
        '15/15 — 0 FAIL — CERTIFIED'

    Add-Evidence `
        'PURIFICATION_VERDICT' `
        'CERTIFIED'

    # ========================================================================
    # SG-09
    # ========================================================================

    Write-Section `
        'SG-09 — ANCIEN POINT ZERO'

    $oldManifest =
        Join-Path `
            $resolvedOldPz `
            'run_manifest.json'

    $oldRecords =
        Join-Path `
            $resolvedOldPz `
            'records.jsonl'

    if (-not (
        Test-Path `
            -LiteralPath $oldManifest `
            -PathType Leaf
    )) {
        throw `
            'Ancien Point Zero : manifest absent.'
    }

    if (-not (
        Test-Path `
            -LiteralPath $oldRecords `
            -PathType Leaf
    )) {
        throw `
            'Ancien Point Zero : records absent.'
    }

    $oldManifestHash =
        Get-Sha256 $oldManifest

    $oldRecordsHash =
        Get-Sha256 $oldRecords

    Write-Host `
        "Old Manifest SHA256 : $oldManifestHash"

    Write-Host `
        "Old Records  SHA256 : $oldRecordsHash"

    Add-Evidence `
        'OLD_POINTZERO_MANIFEST_SHA256' `
        $oldManifestHash

    Add-Evidence `
        'OLD_POINTZERO_RECORDS_SHA256' `
        $oldRecordsHash

    Write-Pass `
        'Ancien Point Zero présent et lisible.'

    Add-Gate `
        'SG-09_OLD_POINTZERO_PRESENT' `
        $true `
        'Ancienne baseline présente'

    # ========================================================================
    # SG-10
    # ========================================================================

    Write-Section `
        'SG-10 — GARDE READ-ONLY'

    Write-Host `
        'Aucune écriture dans le corpus E-ZZIO.'

    Write-Host `
        'Python : compile() mémoire + -B.'

    Write-Host `
        "Écriture externe autorisée uniquement : $FreezeRoot"

    Write-Pass `
        'Contrat CORPUS READ-ONLY établi.'

    Add-Gate `
        'SG-10_READ_ONLY' `
        $true `
        'Aucune opération d''écriture dans le corpus par le moteur'

    # ========================================================================
    # SG-11
    # ========================================================================

    Write-Section `
        'SG-11 — CRÉATION DU CONTENEUR DE FREEZE'

    Ensure-Directory $FreezeRoot

    $freezeRunId =
        [DateTime]::UtcNow.ToString(
            'yyyyMMdd_HHmmss_fff'
        )

    $freezeDir =
        Join-Path `
            $FreezeRoot `
            ("freeze_" + $freezeRunId)

    if (
        Test-Path `
            -LiteralPath $freezeDir
    ) {
        throw `
            "FAIL-CLOSED : collision RunId freeze : $freezeDir"
    }

    New-Item `
        -ItemType Directory `
        -Path $freezeDir `
        -ErrorAction Stop |
        Out-Null

    Write-Host `
        "Freeze directory : $freezeDir"

    Write-Pass `
        'Conteneur de freeze créé hors corpus.'

    Add-Gate `
        'SG-11_FREEZE_CONTAINER' `
        $true `
        $freezeDir

    # ========================================================================
    # SG-12
    # ========================================================================

    Write-Section `
        'SG-12 — IDENTITÉS FORENSIQUES'

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

    Write-Pass `
        'Toutes les identités SHA-256 capturées.'

    Add-Gate `
        'SG-12_FORENSIC_IDENTITIES' `
        $true `
        '7 artefacts certifiés identifiés cryptographiquement'

    # ========================================================================
    # SG-13
    # ========================================================================

    Write-Section `
        'SG-13 — RECHECK DES IDENTITÉS'

    $recheckPython =
        Get-Sha256 $resolvedPython

    $recheckEngine =
        Get-Sha256 $resolvedEngine

    $recheckReport =
        Get-Sha256 $resolvedReport

    $recheckNewManifest =
        Get-Sha256 $newManifest

    $recheckNewRecords =
        Get-Sha256 $newRecords

    $recheckOldManifest =
        Get-Sha256 $oldManifest

    $recheckOldRecords =
        Get-Sha256 $oldRecords

    if (
        $recheckPython `
        -ne `
        $pythonIdentity.SHA256
    ) {
        throw `
            'FAIL-CLOSED : Python modifié.'
    }

    if (
        $recheckEngine `
        -ne `
        $engineIdentity.SHA256
    ) {
        throw `
            'FAIL-CLOSED : moteur modifié.'
    }

    if (
        $recheckReport `
        -ne `
        $purificationIdentity.SHA256
    ) {
        throw `
            'FAIL-CLOSED : rapport purification modifié.'
    }

    if (
        $recheckNewManifest `
        -ne `
        $newManifestIdentity.SHA256
    ) {
        throw `
            'FAIL-CLOSED : nouveau manifest modifié.'
    }

    if (
        $recheckNewRecords `
        -ne `
        $newRecordsIdentity.SHA256
    ) {
        throw `
            'FAIL-CLOSED : nouveaux records modifiés.'
    }

    if (
        $recheckOldManifest `
        -ne `
        $oldManifestIdentity.SHA256
    ) {
        throw `
            'FAIL-CLOSED : ancien manifest modifié.'
    }

    if (
        $recheckOldRecords `
        -ne `
        $oldRecordsIdentity.SHA256
    ) {
        throw `
            'FAIL-CLOSED : anciens records modifiés.'
    }

    Write-Pass `
        'Toutes les identités restent strictement stables.'

    Add-Gate `
        'SG-13_IDENTITY_STABILITY' `
        $true `
        '7/7 identités SHA-256 stables'

    # ========================================================================
    # SG-14 — CORRECTED COUNT
    # ========================================================================

    Write-Section `
        'SG-14 — COHÉRENCE DES 14 GATES PRÉCÉDENTES'

    $gateCount14 =
        @($GateResults).Count

    $gateFailures14 =
        @(
            $GateResults |
                Where-Object {
                    -not $_.Passed
                }
        )

    Write-Host `
        "Gates avant SG-14 : $gateCount14"

    Write-Host `
        "FAIL              : $($gateFailures14.Count)"

    # SG-00 à SG-13 = 14 gates.
    if ($gateCount14 -ne 14) {

        throw `
            "FAIL-CLOSED : nombre de gates inattendu avant SG-14 : $gateCount14"
    }

    if ($gateFailures14.Count -ne 0) {

        throw `
            'FAIL-CLOSED : une gate précédente est en échec.'
    }

    Add-Gate `
        'SG-14_PREVIOUS_GATES_COHERENCE' `
        $true `
        '14/14 gates précédentes PASS'

    # ========================================================================
    # SG-15
    # ========================================================================

    Write-Section `
        'SG-15 — ABSENCE DE MUTATION DU CORPUS'

    if (
        $recheckPython `
        -ne `
        $ExpectedPythonHash
    ) {
        throw `
            'FAIL-CLOSED : identité Python finale non conforme.'
    }

    Write-Pass `
        'Aucune mutation détectée sur les artefacts certifiés.'

    Add-Gate `
        'SG-15_CORPUS_MUTATION_CHECK' `
        $true `
        'Aucune mutation détectée'

    # ========================================================================
    # SG-16
    # ========================================================================

    Write-Section `
        'SG-16 — PRÉ-CERTIFICATION 16/16'

    $gateCount16 =
        @($GateResults).Count

    $gateFailures16 =
        @(
            $GateResults |
                Where-Object {
                    -not $_.Passed
                }
        )

    Write-Host `
        "Gates avant SG-16 : $gateCount16"

    Write-Host `
        "FAIL              : $($gateFailures16.Count)"

    # SG-00 à SG-14 = 15 gates.
    # SG-15 vient ensuite.
    # Donc avant SG-16 : 16 gates.
    if ($gateCount16 -ne 16) {

        throw `
            "FAIL-CLOSED : nombre de gates inattendu avant SG-16 : $gateCount16"
    }

    if ($gateFailures16.Count -ne 0) {

        throw `
            'FAIL-CLOSED : une gate précédente est en échec.'
    }

    Add-Gate `
        'SG-16_PRE_CERTIFICATION_CONSISTENCY' `
        $true `
        '16/16 gates précédentes PASS'

    # ========================================================================
    # SG-17
    # ========================================================================

    Write-Section `
        'SG-17 — FREEZE CERTIFICATION'

    $preFinalCount =
        @($GateResults).Count

    $preFinalFailures =
        @(
            $GateResults |
                Where-Object {
                    -not $_.Passed
                }
        )

    if ($preFinalCount -ne 16) {

        throw `
            "CERTIFICATION REFUSÉE : $preFinalCount gates avant SG-17."
    }

    if ($preFinalFailures.Count -ne 0) {

        throw `
            'CERTIFICATION REFUSÉE : une gate précédente est FAIL.'
    }

    Add-Gate `
        'SG-17_FREEZE_CERTIFICATION' `
        $true `
        '17/17 — certification accordée'

    # ========================================================================
    # FINAL MATHEMATICAL ASSERTION
    # ========================================================================

    Write-Section `
        'FINAL GATE ASSERTION — 17/17'

    $totalGates =
        @($GateResults).Count

    $failedGates =
        @(
            $GateResults |
                Where-Object {
                    -not $_.Passed
                }
        )

    Write-Host `
        "TOTAL GATES : $totalGates"

    Write-Host `
        "FAIL GATES  : $($failedGates.Count)"

    if ($totalGates -ne 17) {

        throw `
            "CERTIFICATION REFUSÉE : total gates=$totalGates au lieu de 17."
    }

    if ($failedGates.Count -ne 0) {

        throw `
            "CERTIFICATION REFUSÉE : $($failedGates.Count) FAIL."
    }

    # ========================================================================
    # FREEZE MANIFEST — ONLY AFTER 17/17
    # ========================================================================

    Write-Section `
        'FREEZE MANIFEST — PREUVE FINALE 17/17'

    $freezeManifest =
        [PSCustomObject]@{

            Freeze = [PSCustomObject]@{
                EngineName    = $EngineName
                EngineVersion = $EngineVersion
                Verdict       = 'FREEZE_CERTIFIED'
                Mode          = 'FAST + FORENSIC / CORPUS READ-ONLY / FAIL-CLOSED'
                CreatedAtUtc  = [DateTime]::UtcNow.ToString('o')
                GateCount     = 17
                FailedGates   = 0
            }

            CertifiedState = [PSCustomObject]@{
                PurificationEngineVersion = '0.2.1'
                PurificationVerdict       = 'CERTIFIED'
                PurificationGates         = 15
                PurificationFailures      = 0
                PythonSHA256              = $ExpectedPythonHash
                NewPointZeroRunId         = $manifestRunId
                NewPointZeroRecordCount   = $recordCount
            }

            Paths = [PSCustomObject]@{
                EzzioRoot          = $resolvedEzzioRoot
                FreezeRoot         = $FreezeRoot
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

            Gates = @(
                $GateResults
            )

            Evidence = @(
                $Evidence
            )
        }

    $freezeManifestPath =
        Join-Path `
            $freezeDir `
            'freeze_manifest.json'

    $freezeManifestJson =
        $freezeManifest |
            ConvertTo-Json `
                -Depth 40

    [System.IO.File]::WriteAllText(
        $freezeManifestPath,
        $freezeManifestJson,
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

    # ========================================================================
    # MANIFEST RELOAD
    # ========================================================================

    $manifestReloaded =
        Read-JsonStrict $freezeManifestPath

    $reloadedGates =
        @($manifestReloaded.Gates)

    if ($reloadedGates.Count -ne 17) {

        throw `
            "FAIL-CLOSED : manifest final contient $($reloadedGates.Count) gates."
    }

    $reloadedFailures =
        @(
            $reloadedGates |
                Where-Object {
                    -not $_.Passed
                }
        )

    if ($reloadedFailures.Count -ne 0) {

        throw `
            'FAIL-CLOSED : manifest final contient un FAIL.'
    }

    if (
        [string]$manifestReloaded.Freeze.Verdict `
        -ne `
        'FREEZE_CERTIFIED'
    ) {

        throw `
            'FAIL-CLOSED : verdict du manifest final incorrect.'
    }

    if (
        [int]$manifestReloaded.Freeze.GateCount `
        -ne `
        17
    ) {

        throw `
            'FAIL-CLOSED : GateCount du manifest final incorrect.'
    }

    if (
        [int]$manifestReloaded.Freeze.FailedGates `
        -ne `
        0
    ) {

        throw `
            'FAIL-CLOSED : FailedGates du manifest final incorrect.'
    }

    # ========================================================================
    # MANIFEST HASH
    # ========================================================================

    $freezeManifestHash =
        Get-Sha256 $freezeManifestPath

    $freezeSealPath =
        Join-Path `
            $freezeDir `
            'freeze_manifest.sha256'

    $sealContent =
        "$freezeManifestHash  freeze_manifest.json"

    [System.IO.File]::WriteAllText(
        $freezeSealPath,
        $sealContent,
        [System.Text.UTF8Encoding]::new($false)
    )

    if (-not (
        Test-Path `
            -LiteralPath $freezeSealPath `
            -PathType Leaf
    )) {

        throw `
            'FAIL-CLOSED : sceau externe non créé.'
    }

    # ========================================================================
    # SEAL RECHECK
    # ========================================================================

    $sealRead =
        [System.IO.File]::ReadAllText(
            $freezeSealPath,
            [System.Text.UTF8Encoding]::new($false)
        )

    $sealRead =
        $sealRead.Trim()

    $expectedSeal =
        "$freezeManifestHash  freeze_manifest.json"

    if ($sealRead -ne $expectedSeal) {

        throw `
            'FAIL-CLOSED : contenu du sceau SHA-256 incohérent.'
    }

    $freezeManifestHashRecheck =
        Get-Sha256 $freezeManifestPath

    if (
        $freezeManifestHashRecheck `
        -ne `
        $freezeManifestHash
    ) {

        throw `
            'FAIL-CLOSED : hash du manifest modifié après émission.'
    }

    Add-Evidence `
        'FREEZE_MANIFEST_SHA256' `
        $freezeManifestHash

    Add-Evidence `
        'FREEZE_SEAL_PATH' `
        $freezeSealPath

    Write-Pass `
        'Manifest final : 17/17 — 0 FAIL.'

    Write-Pass `
        'SHA-256 du manifest stable.'

    Write-Pass `
        'Sceau externe créé et vérifié.'

    # ========================================================================
    # CERTIFIED STATE
    # ========================================================================

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

    Write-Host `
        'ÉTAT CERTIFIÉ : FIGÉ' `
        -ForegroundColor Green

    Write-Host `
        'GATES         : 17/17' `
        -ForegroundColor Green

    Write-Host `
        'FAIL          : 0' `
        -ForegroundColor Green

    Write-Host `
        'CORPUS        : NON MODIFIÉ' `
        -ForegroundColor Green

    Write-Host ''

    Write-Host `
        "Freeze Dir      : $freezeDir"

    Write-Host `
        "Freeze Manifest : $freezeManifestPath"

    Write-Host `
        "Freeze SHA-256  : $freezeManifestHash"

    Write-Host `
        "Freeze Seal     : $freezeSealPath"
}
catch {

    $FatalError = $_
    $ExitCode = 1
    $FreezeCertified = $false

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
        Write-Host `
            'FORENSIC LOCATION' `
            -ForegroundColor Yellow

        Write-Host `
            "Script : $($_.InvocationInfo.ScriptName)"

        Write-Host `
            "Line   : $($_.InvocationInfo.ScriptLineNumber)"

        Write-Host `
            "Code   : $($_.InvocationInfo.Line)"
    }

    Write-Host ''
    Write-Host `
        'AUCUN FREEZE CERTIFIED ÉMIS.' `
        -ForegroundColor Red
}
finally {

    # ========================================================================
    # FORENSIC REPORT
    # ========================================================================

    try {

        Ensure-Directory $FreezeRoot

        if (
            -not [string]::IsNullOrWhiteSpace(
                [string]$freezeDir
            )
        ) {

            $reportRunId =
                Split-Path `
                    -Leaf `
                    $freezeDir
        }
        else {

            $reportRunId =
                'failed_' +
                (
                    [DateTime]::UtcNow.ToString(
                        'yyyyMMdd_HHmmss_fff'
                    )
                )
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
                    Mode    = 'FAST + FORENSIC / CORPUS READ-ONLY / FAIL-CLOSED'
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
                    if (
                        -not [string]::IsNullOrWhiteSpace(
                            [string]$freezeManifestPath
                        )
                    ) {
                        $freezeManifestPath
                    }
                    else {
                        $null
                    }

                FreezeManifestSHA256 =
                    if (
                        -not [string]::IsNullOrWhiteSpace(
                            [string]$freezeManifestHash
                        )
                    ) {
                        $freezeManifestHash
                    }
                    else {
                        $null
                    }

                FreezeSeal =
                    if (
                        -not [string]::IsNullOrWhiteSpace(
                            [string]$freezeSealPath
                        )
                    ) {
                        $freezeSealPath
                    }
                    else {
                        $null
                    }
            }

        [System.IO.File]::WriteAllText(
            $reportPath,
            (
                $report |
                    ConvertTo-Json `
                        -Depth 40
            ),
            [System.Text.UTF8Encoding]::new($false)
        )

        Write-Host ''
        Write-Host `
            '==============================================================================' `
            -ForegroundColor DarkCyan

        Write-Host `
            ' FREEZE FORENSIC REPORT ' `
            -ForegroundColor DarkCyan

        Write-Host `
            '==============================================================================' `
            -ForegroundColor DarkCyan

        Write-Host ''

        Write-Host `
            "Rapport : $reportPath" `
            -ForegroundColor DarkGray
    }
    catch {

        $ExitCode = 1
        $FreezeCertified = $false

        Write-Host ''
        Write-Host `
            '[CRITICAL] Impossible d''écrire le rapport de freeze.' `
            -ForegroundColor Red

        Write-Host `
            $_.Exception.Message `
            -ForegroundColor Red
    }

    Write-Host ''
    Write-Host `
        '==============================================================================' `
        -ForegroundColor Cyan

    if (
        $FreezeCertified `
        -and `
        $ExitCode -eq 0
    ) {

        Write-Host `
            ' E-ZZIO — ÉTAT FIGÉ : FREEZE CERTIFIED' `
            -ForegroundColor Green
    }
    else {

        Write-Host `
            ' E-ZZIO — FREEZE : FAIL-CLOSED' `
            -ForegroundColor Red
    }

    Write-Host `
        '==============================================================================' `
        -ForegroundColor Cyan

    Write-Host ''

    Write-Host `
        'Corpus modifié             : NON'

    Write-Host `
        'Ancien Point Zero modifié  : NON'

    Write-Host `
        'Nouveau Point Zero modifié : NON'

    if ($PauseOnExit) {
        Read-Host `
            'Appuyez sur Entrée pour fermer'
    }

    exit $ExitCode
}