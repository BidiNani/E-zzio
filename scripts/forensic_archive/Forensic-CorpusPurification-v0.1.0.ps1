# ============================================================================
# E-ZZIO — CONTROLLED CORPUS PURIFICATION v0.1.0
# ============================================================================
# PURPOSE
#   Traiter explicitement une aberration extension/contenu détectée
#   par le moteur forensic.
#
# TARGET
#   runtime\audit\v7_full_intelligence_scan.ps1
#
# EXPECTED TRUTH
#   Le contenu est Python.
#   L'extension .ps1 est donc incohérente.
#
# DOCTRINE
#   - READ-ONLY par défaut.
#   - FAIL-CLOSED.
#   - Aucune mutation silencieuse.
#   - Aucun écrasement.
#   - Aucun nettoyage.
#   - Aucun changement du Point Zero.
#   - Aucun PASS artificiel.
#   - Le SHA-256 historique doit correspondre AVANT mutation.
#   - Une mutation explicite invalide volontairement l'ancien Point Zero.
#   - Le nouveau Point Zero devra être généré séparément.
#
# IMPORTANT
#   Ce script ne reconstruit PAS le Point Zero.
#   Il ne tente PAS de rendre l'ancien Point Zero compatible.
#   Il sépare strictement :
#
#       ANCIEN ÉTAT
#           ↓
#       MUTATION EXPLICITE
#           ↓
#       NOUVEL ÉTAT
#           ↓
#       NOUVEAU POINT ZERO
#
# VERSION
#   0.1.0
# ============================================================================

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$PointZeroDir,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Target,

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$ForensicRoot = 'G:\AI\_forensic',

    [Parameter(Mandatory = $false)]
    [ValidateNotNullOrEmpty()]
    [string]$ExpectedDestinationExtension = '.py',

    [Parameter(Mandatory = $false)]
    [switch]$ApplyRename,

    [Parameter(Mandatory = $false)]
    [switch]$PauseOnExit
)

# ============================================================================
# STRICT MODE
# ============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# GLOBAL STATE
# ============================================================================

$script:EngineVersion = '0.1.0'
$script:ExitCode = 1
$script:FatalError = $null
$script:MutationPerformed = $false
$script:GateResults = [System.Collections.Generic.List[object]]::new()
$script:Warnings = [System.Collections.Generic.List[string]]::new()
$script:StartUtc = [DateTime]::UtcNow

$sourceRoot = $null
$physicalPath = $null
$destinationPath = $null
$recordResult = $null
$recordHash = $null
$physicalHashBefore = $null
$physicalHashAfter = $null

# ============================================================================
# OUTPUT
# ============================================================================

function Write-Section {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )

    Write-Host ''
    Write-Host '==============================================================================' -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host '==============================================================================' -ForegroundColor Cyan
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

function Write-Warn {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    $script:Warnings.Add($Message) | Out-Null
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Add-GateResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Gate,

        [Parameter(Mandatory = $true)]
        [bool]$Passed,

        [Parameter(Mandatory = $true)]
        [string]$Detail
    )

    $script:GateResults.Add(
        [PSCustomObject]@{
            Gate    = $Gate
            Passed  = $Passed
            Detail  = $Detail
            TimeUtc = [DateTime]::UtcNow.ToString('o')
        }
    ) | Out-Null
}

# ============================================================================
# PATH
# ============================================================================

function Resolve-CanonicalPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $resolved = Resolve-Path `
        -LiteralPath $Path `
        -ErrorAction Stop

    return [System.IO.Path]::GetFullPath($resolved.Path)
}

function Test-PathInside {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Child,

        [Parameter(Mandatory = $true)]
        [string]$Parent
    )

    $childCanonical  = [System.IO.Path]::GetFullPath($Child)
    $parentCanonical = [System.IO.Path]::GetFullPath($Parent)

    if (-not $parentCanonical.EndsWith(
        [System.IO.Path]::DirectorySeparatorChar
    )) {
        $parentCanonical += [System.IO.Path]::DirectorySeparatorChar
    }

    return $childCanonical.StartsWith(
        $parentCanonical,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

# ============================================================================
# SHA256
# ============================================================================

function Get-FileSha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return (
        Get-FileHash `
            -LiteralPath $Path `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash.ToLowerInvariant()
}

# ============================================================================
# JSON
# ============================================================================

function Read-JsonFileStrict {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
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
# RECORD SEARCH
# ============================================================================

function Find-RecordForRelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RecordsPath,

        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    if (-not (Test-Path -LiteralPath $RecordsPath -PathType Leaf)) {
        throw "records.jsonl absent : $RecordsPath"
    }

    $normalizedTarget =
        $RelativePath.Replace('\','/').TrimStart('/')

    $lineNumber = 0

    foreach ($line in [System.IO.File]::ReadLines($RecordsPath)) {

        $lineNumber++

        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        try {
            $record =
                $line |
                ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            continue
        }

        $candidate = $null

        foreach ($propertyName in @(
            'Path',
            'RelativePath',
            'relPath',
            'relative_path',
            'File'
        )) {

            if (
                $record.PSObject.Properties.Name -contains
                $propertyName
            ) {

                $candidate = [string]$record.$propertyName

                if (-not [string]::IsNullOrWhiteSpace($candidate)) {
                    break
                }
            }
        }

        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }

        $candidateNormalized =
            $candidate.Replace('\','/').TrimStart('/')

        if ($candidateNormalized -ieq $normalizedTarget) {

            return [PSCustomObject]@{
                LineNumber = $lineNumber
                Record     = $record
            }
        }
    }

    return $null
}

# ============================================================================
# PYTHON FINGERPRINT
# ============================================================================

function Test-PythonFingerprint {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [string[]]$Lines
    )

    if ($null -eq $Lines) {
        return [PSCustomObject]@{
            IsPythonLike = $false
            Score        = 0
            Evidence     = @()
        }
    }

    $score = 0
    $evidence = [System.Collections.Generic.List[string]]::new()

    foreach ($line in @($Lines)) {

        if ($null -eq $line) {
            continue
        }

        $text = [string]$line

        if ($text -match '^\s*from\s+[A-Za-z0-9_.]+\s+import\s+') {
            $score += 3
            $evidence.Add('from ... import ...') | Out-Null
        }

        if ($text -match '^\s*import\s+[A-Za-z0-9_.]+') {
            $score += 2
            $evidence.Add('import ...') | Out-Null
        }

        if ($text -match '^\s*def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(') {
            $score += 3
            $evidence.Add('def ...') | Out-Null
        }

        if ($text -match '^\s*class\s+[A-Za-z_][A-Za-z0-9_]*\s*[:\(]') {
            $score += 2
            $evidence.Add('class declaration') | Out-Null
        }

        if ($text -match 'json\.dumps\s*\(') {
            $score += 3
            $evidence.Add('json.dumps(...)') | Out-Null
        }

        if ($text -match 'datetime\.utcnow\s*\(') {
            $score += 2
            $evidence.Add('datetime.utcnow(...)') | Out-Null
        }

        if ($text -match 'f["''].*\{[^}]+\}') {
            $score += 2
            $evidence.Add('Python f-string') | Out-Null
        }

        if ($text -match '^\s*for\s+\w+\s+in\s+') {
            $score += 2
            $evidence.Add('for ... in ...') | Out-Null
        }

        if ($text -match '^\s*if\s+.+:\s*$') {
            $score += 1
            $evidence.Add('if ...:') | Out-Null
        }
    }

    return [PSCustomObject]@{
        IsPythonLike = ($score -ge 5)
        Score        = $score
        Evidence     = @(
            $evidence | Select-Object -Unique
        )
    }
}

# ============================================================================
# SAMPLE
# ============================================================================

function Get-SafeTextSample {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $false)]
        [int]$MaxLines = 300
    )

    $lines =
        [System.Collections.Generic.List[string]]::new()

    foreach ($line in [System.IO.File]::ReadLines($Path)) {

        $lines.Add([string]$line)

        if ($lines.Count -ge $MaxLines) {
            break
        }
    }

    return $lines.ToArray()
}

# ============================================================================
# OUTPUT DIRECTORY
# ============================================================================

function Initialize-ForensicOutput {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Root,

        [Parameter(Mandatory = $true)]
        [string]$RunId
    )

    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {

        New-Item `
            -ItemType Directory `
            -Path $Root `
            -Force `
            -ErrorAction Stop |
            Out-Null
    }

    $dir = Join-Path $Root ("run_" + $RunId)

    if (-not (Test-Path -LiteralPath $dir -PathType Container)) {

        New-Item `
            -ItemType Directory `
            -Path $dir `
            -Force `
            -ErrorAction Stop |
            Out-Null
    }

    return $dir
}

# ============================================================================
# MAIN
# ============================================================================

try {

    Write-Section "E-ZZIO — CONTROLLED CORPUS PURIFICATION v$($script:EngineVersion)"

    Write-Host "Mode              : $(if ($ApplyRename) { 'EXPLICIT MUTATION' } else { 'READ-ONLY / FORENSIC' })"
    Write-Host "PointZeroDir      : $PointZeroDir"
    Write-Host "Target            : $Target"
    Write-Host "Expected New Ext  : $ExpectedDestinationExtension"
    Write-Host "ForensicRoot      : $ForensicRoot"

    # ========================================================================
    # SG-00
    # ========================================================================

    Write-Section "SG-00 — PREFLIGHT"

    if (-not (Test-Path -LiteralPath $PointZeroDir -PathType Container)) {
        throw "Point Zero inexistant."
    }

    $manifestPath =
        Join-Path $PointZeroDir 'run_manifest.json'

    $recordsPath =
        Join-Path $PointZeroDir 'records.jsonl'

    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Manifest absent."
    }

    if (-not (Test-Path -LiteralPath $recordsPath -PathType Leaf)) {
        throw "records.jsonl absent."
    }

    Write-Pass "Point Zero + Manifest + Records présents"

    Add-GateResult `
        'SG-00_PREFLIGHT' `
        $true `
        'Infrastructure Point Zero disponible'

    # ========================================================================
    # SG-01
    # ========================================================================

    Write-Section "SG-01 — SOURCE ROOT"

    $manifest =
        Read-JsonFileStrict $manifestPath

    if (
        -not (
            $manifest.PSObject.Properties.Name -contains
            'RootPathScanned'
        )
    ) {
        throw "RootPathScanned absent."
    }

    $sourceRootRaw =
        [string]$manifest.RootPathScanned

    if ([string]::IsNullOrWhiteSpace($sourceRootRaw)) {
        throw "RootPathScanned vide."
    }

    $sourceRoot =
        Resolve-CanonicalPath $sourceRootRaw

    Write-Host "SourceRoot : $sourceRoot"

    Add-GateResult `
        'SG-01_SOURCE_ROOT' `
        $true `
        $sourceRoot

    # ========================================================================
    # SG-02
    # ========================================================================

    Write-Section "SG-02 — RÉSOLUTION PHYSIQUE"

    $targetNormalized =
        $Target.Replace('/','\').TrimStart('\')

    $physicalPath =
        [System.IO.Path]::GetFullPath(
            (Join-Path $sourceRoot $targetNormalized)
        )

    $destinationPath =
        [System.IO.Path]::ChangeExtension(
            $physicalPath,
            $ExpectedDestinationExtension
        )

    Write-Host "PhysicalPath : $physicalPath"
    Write-Host "Destination  : $destinationPath"

    if (
        -not (
            Test-PathInside `
                -Child $physicalPath `
                -Parent $sourceRoot
        )
    ) {
        throw "PATH TRAVERSAL détecté."
    }

    if (
        -not (
            Test-PathInside `
                -Child $destinationPath `
                -Parent $sourceRoot
        )
    ) {
        throw "Destination hors SourceRoot."
    }

    if (-not (Test-Path -LiteralPath $physicalPath -PathType Leaf)) {
        throw "Fichier source absent."
    }

    Write-Pass "Source et destination confinées au SourceRoot"

    Add-GateResult `
        'SG-02_PHYSICAL_CONTAINMENT' `
        $true `
        'Source et destination confinées'

    # ========================================================================
    # SG-03
    # ========================================================================

    Write-Section "SG-03 — SHA-256 AVANT MUTATION"

    $physicalHashBefore =
        Get-FileSha256 $physicalPath

    Write-Host "SHA-256 physique : $physicalHashBefore"

    Add-GateResult `
        'SG-03_PHYSICAL_HASH' `
        $true `
        $physicalHashBefore

    # ========================================================================
    # SG-04
    # ========================================================================

    Write-Section "SG-04 — PARITÉ AVEC POINT ZERO"

    $recordResult =
        Find-RecordForRelativePath `
            -RecordsPath $recordsPath `
            -RelativePath $targetNormalized

    if ($null -eq $recordResult) {
        throw "Record Point Zero introuvable."
    }

    Write-Pass "Record trouvé à la ligne $($recordResult.LineNumber)"

    $record =
        $recordResult.Record

    foreach ($propertyName in @(
        'SHA256',
        'Sha256',
        'sha256',
        'Hash',
        'hash',
        'FileHash'
    )) {

        if (
            $record.PSObject.Properties.Name -contains
            $propertyName
        ) {

            $candidate =
                [string]$record.$propertyName

            if (-not [string]::IsNullOrWhiteSpace($candidate)) {

                $recordHash =
                    $candidate.ToLowerInvariant()

                break
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($recordHash)) {
        throw "SHA-256 absent du record Point Zero."
    }

    Write-Host "SHA-256 Point Zero : $recordHash"

    if ($physicalHashBefore -ne $recordHash) {

        throw `
            "HASH MISMATCH AVANT MUTATION : physique=$physicalHashBefore / PointZero=$recordHash"
    }

    Write-Pass "SHA-256 physique == Point Zero"

    Add-GateResult `
        'SG-04_POINTZERO_HASH_PARITY' `
        $true `
        'Hash historique intact'

    # ========================================================================
    # SG-05
    # ========================================================================

    Write-Section "SG-05 — PREUVE DU TYPE DE CONTENU"

    $sample =
        Get-SafeTextSample `
            -Path $physicalPath `
            -MaxLines 300

    $fingerprint =
        Test-PythonFingerprint `
            -Lines @($sample)

    Write-Host "Python score : $($fingerprint.Score)"
    Write-Host "PythonLike   : $($fingerprint.IsPythonLike)"

    foreach ($evidence in @($fingerprint.Evidence)) {

        Write-Host "  - $evidence" `
            -ForegroundColor DarkYellow
    }

    if (-not $fingerprint.IsPythonLike) {

        throw `
            "Le contenu n'est pas suffisamment identifié comme Python. Mutation interdite."
    }

    Write-Pass "Contenu fortement identifié comme Python"

    Add-GateResult `
        'SG-05_CONTENT_TRUTH' `
        $true `
        "Python fingerprint score=$($fingerprint.Score)"

    # ========================================================================
    # SG-06
    # ========================================================================

    Write-Section "SG-06 — DESTINATION"

    if (Test-Path -LiteralPath $destinationPath) {

        throw `
            "DESTINATION DÉJÀ EXISTANTE : $destinationPath"
    }

    Write-Pass "Destination libre"

    Add-GateResult `
        'SG-06_DESTINATION_FREE' `
        $true `
        'Aucun écrasement possible'

    # ========================================================================
    # READ-ONLY STOP
    # ========================================================================

    if (-not $ApplyRename) {

        Write-Section "READ-ONLY — PLAN DE MUTATION"

        Write-Host ''
        Write-Host 'AUCUNE MUTATION EFFECTUÉE.' `
            -ForegroundColor Green

        Write-Host ''
        Write-Host 'Action proposée :' `
            -ForegroundColor Yellow

        Write-Host "  $physicalPath"
        Write-Host '       ↓'
        Write-Host "  $destinationPath"

        Write-Host ''
        Write-Host "Ancien SHA-256 : $physicalHashBefore"
        Write-Host ''
        Write-Host 'IMPORTANT :' `
            -ForegroundColor Yellow
        Write-Host 'Le Point Zero actuel deviendra volontairement OBSOLÈTE.'
        Write-Host 'Il ne sera ni modifié ni falsifié.'
        Write-Host 'Un NOUVEAU Point Zero devra être généré après mutation.'

        Add-GateResult `
            'SG-07_MUTATION_AUTHORIZATION' `
            $true `
            'Mutation non demandée : mode READ-ONLY'

        $script:ExitCode = 0
    }
    else {

        # ====================================================================
        # EXPLICIT MUTATION
        # ====================================================================

        Write-Section "SG-07 — MUTATION EXPLICITEMENT AUTORISÉE"

        Write-Host ''
        Write-Host 'ATTENTION' -ForegroundColor Red
        Write-Host 'Une mutation physique va être effectuée.'
        Write-Host ''
        Write-Host "SOURCE : $physicalPath"
        Write-Host "DEST   : $destinationPath"
        Write-Host ''

        Rename-Item `
            -LiteralPath $physicalPath `
            -NewName ([System.IO.Path]::GetFileName($destinationPath)) `
            -ErrorAction Stop

        $script:MutationPerformed = $true

        Write-Pass "Renommage physique effectué"

        Add-GateResult `
            'SG-07_EXPLICIT_RENAME' `
            $true `
            'Renommage explicitement autorisé'

        # ====================================================================
        # SG-08
        # ====================================================================

        Write-Section "SG-08 — POST-MUTATION INTEGRITY"

        if (Test-Path -LiteralPath $physicalPath -PathType Leaf) {

            throw `
                'Échec intégrité : ancien chemin encore présent.'
        }

        if (-not (Test-Path -LiteralPath $destinationPath -PathType Leaf)) {

            throw `
                'Échec intégrité : destination absente après renommage.'
        }

        $physicalHashAfter =
            Get-FileSha256 $destinationPath

        Write-Host "SHA-256 après renommage : $physicalHashAfter"

        if ($physicalHashAfter -ne $physicalHashBefore) {

            throw `
                "HASH MODIFIÉ PAR LE RENOMMAGE : avant=$physicalHashBefore / après=$physicalHashAfter"
        }

        Write-Pass "Contenu cryptographiquement identique après renommage"

        Add-GateResult `
            'SG-08_POST_RENAME_HASH' `
            $true `
            'SHA-256 invariant'

        # ====================================================================
        # SG-09
        # ====================================================================

        Write-Section "SG-09 — ANCIEN POINT ZERO"

        Write-Host ''
        Write-Host 'Le Point Zero historique N''EST PAS modifié.' `
            -ForegroundColor Green

        Write-Host 'Il représente désormais un état historique antérieur à la mutation.'

        Add-GateResult `
            'SG-09_POINTZERO_IMMUTABILITY' `
            $true `
            'Point Zero historique non modifié'

        # ====================================================================
        # FINAL MUTATION VERDICT
        # ====================================================================

        Write-Section "MUTATION TERMINÉE"

        Write-Host ''
        Write-Host 'CORPUS MUTÉ EXPLICITEMENT.' `
            -ForegroundColor Yellow

        Write-Host ''
        Write-Host 'NOUVELLE VÉRITÉ PHYSIQUE :' `
            -ForegroundColor Cyan

        Write-Host "  $destinationPath"

        Write-Host ''
        Write-Host 'PROCHAINE ÉTAPE OBLIGATOIRE :' `
            -ForegroundColor Yellow

        Write-Host '  1. Générer un NOUVEAU Point Zero.'
        Write-Host '  2. Générer une NOUVELLE topologie.'
        Write-Host '  3. Relancer le Semantic Engine.'
        Write-Host '  4. Rejouer toutes les Quality Gates.'
        Write-Host '  5. Seulement alors rechercher CERTIFIED / FROZEN.'

        $script:ExitCode = 0
    }
}
catch {

    $script:FatalError = $_
    $script:ExitCode = 1

    Write-Section "FAIL-CLOSED"

    Write-Host ''
    Write-Host "ERROR : $($_.Exception.Message)" `
        -ForegroundColor Red

    Write-Host ''
    Write-Host "TYPE  : $($_.Exception.GetType().FullName)" `
        -ForegroundColor Red

    if ($_.InvocationInfo) {

        Write-Host ''
        Write-Host 'FORENSIC LOCATION' `
            -ForegroundColor Yellow

        Write-Host "Script : $($_.InvocationInfo.ScriptName)"
        Write-Host "Line   : $($_.InvocationInfo.ScriptLineNumber)"
        Write-Host "Code   : $($_.InvocationInfo.Line)"
    }

    Write-Host ''
    Write-Host 'FAIL-CLOSED : aucune certification émise.' `
        -ForegroundColor Red
}

finally {

    # ========================================================================
    # REPORT
    # ========================================================================

    try {

        $runId =
            Split-Path `
                -Leaf `
                ([System.IO.Path]::GetFullPath($PointZeroDir))

        $outputRoot =
            Join-Path $ForensicRoot 'CorpusPurification'

        $outputDir =
            Initialize-ForensicOutput `
                -Root $outputRoot `
                -RunId $runId

        $reportPath =
            Join-Path $outputDir 'corpus_purification_report.json'

        $report = [PSCustomObject]@{

            Engine = [PSCustomObject]@{
                Name    = 'E-ZZIO — CONTROLLED CORPUS PURIFICATION'
                Version = $script:EngineVersion
                Mode    = if ($ApplyRename) {
                    'EXPLICIT_MUTATION'
                }
                else {
                    'READ_ONLY / FORENSIC'
                }
            }

            Execution = [PSCustomObject]@{
                StartedAtUtc  = $script:StartUtc.ToString('o')
                FinishedAtUtc = [DateTime]::UtcNow.ToString('o')
                ExitCode      = $script:ExitCode
            }

            Inputs = [PSCustomObject]@{
                PointZeroDir = $PointZeroDir
                Target       = $Target
            }

            Evidence = [PSCustomObject]@{
                SourceRoot          = $sourceRoot
                PhysicalPath        = $physicalPath
                DestinationPath     = $destinationPath
                PointZeroHash       = $recordHash
                PhysicalHashBefore  = $physicalHashBefore
                PhysicalHashAfter   = $physicalHashAfter
                PythonFingerprint   = $true
            }

            Mutation = [PSCustomObject]@{
                Requested = [bool]$ApplyRename
                Performed = $script:MutationPerformed
                RenameOnly = $true
                CorpusModified = $script:MutationPerformed
                PointZeroModified = $false
                Silent = $false
            }

            Gates = @(
                $script:GateResults
            )

            Warnings = @(
                $script:Warnings
            )

            FatalError =
                if ($null -ne $script:FatalError) {

                    [PSCustomObject]@{
                        Type =
                            $script:FatalError.Exception.GetType().FullName

                        Message =
                            $script:FatalError.Exception.Message
                    }
                }
                else {
                    $null
                }

            Verdict =
                if ($script:ExitCode -eq 0) {
                    if ($script:MutationPerformed) {
                        'MUTATION_COMPLETE_NEW_POINTZERO_REQUIRED'
                    }
                    else {
                        'READ_ONLY_PLAN_VALIDATED'
                    }
                }
                else {
                    'FAIL_CLOSED'
                }
        }

        [System.IO.File]::WriteAllText(
            $reportPath,
            (
                $report |
                ConvertTo-Json -Depth 15
            ),
            [System.Text.UTF8Encoding]::new($false)
        )

        Write-Host ''
        Write-Host '==============================================================================' `
            -ForegroundColor DarkCyan
        Write-Host ' FORENSIC REPORT' `
            -ForegroundColor DarkCyan
        Write-Host '==============================================================================' `
            -ForegroundColor DarkCyan

        Write-Host "Rapport : $reportPath" `
            -ForegroundColor DarkGray
    }
    catch {

        Write-Host ''
        Write-Host '[CRITICAL] Rapport forensic impossible.' `
            -ForegroundColor Red

        Write-Host $_.Exception.Message `
            -ForegroundColor Red

        $script:ExitCode = 1
    }

    Write-Host ''
    Write-Host '==============================================================================' `
        -ForegroundColor Cyan

    if ($script:ExitCode -eq 0) {

        if ($script:MutationPerformed) {

            Write-Host `
                ' E-ZZIO — PURIFICATION : MUTATION EXPLICITE TERMINÉE' `
                -ForegroundColor Yellow
        }
        else {

            Write-Host `
                ' E-ZZIO — PURIFICATION : READ-ONLY PLAN VALIDÉ' `
                -ForegroundColor Green
        }
    }
    else {

        Write-Host `
            ' E-ZZIO — PURIFICATION : FAIL-CLOSED' `
            -ForegroundColor Red
    }

    Write-Host '==============================================================================' `
        -ForegroundColor Cyan

    Write-Host ''

    if ($script:MutationPerformed) {

        Write-Host 'Corpus : MODIFIÉ EXPLICITEMENT' `
            -ForegroundColor Yellow

        Write-Host 'Point Zero historique : NON MODIFIÉ' `
            -ForegroundColor Green

        Write-Host 'Nouveau Point Zero : OBLIGATOIRE' `
            -ForegroundColor Yellow
    }
    else {

        Write-Host 'Corpus : NON MODIFIÉ' `
            -ForegroundColor Green

        Write-Host 'Point Zero : NON MODIFIÉ' `
            -ForegroundColor Green

        Write-Host 'Renommage : AUCUN' `
            -ForegroundColor Green
    }

    Write-Host ''

    if ($PauseOnExit) {

        Read-Host 'Appuyez sur Entrée pour fermer'
    }
}

exit $script:ExitCode