# ============================================================================
# E-ZZIO — FORENSIC EXTENSION TRUTH v0.1.2
# ============================================================================
# MODE       : READ-ONLY / FORENSIC / FAIL-CLOSED
# PURPOSE    : Vérifier la cohérence extension <-> contenu d'un fichier.
#
# DOCTRINE
#   - Aucun fichier du corpus n'est modifié.
#   - Aucun renommage.
#   - Aucun nettoyage destructif.
#   - Aucun PASS artificiel.
#   - Toute anomalie est explicitement enregistrée.
#   - Toute exception provoque FAIL-CLOSED.
#   - Le rapport forensic est écrit uniquement hors du corpus.
#   - Aucun exit brutal : la fenêtre reste disponible pour inspection.
#
# IMPORTANT
#   Ce fichier doit être exécuté comme un .ps1.
#   Ne pas coller son contenu ligne par ligne dans le prompt interactif.
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
    [switch]$PauseOnExit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# GLOBAL STATE
# ============================================================================

$script:EngineVersion = '0.1.2'
$script:ExitCode = 1
$script:FatalError = $null

$script:GateResults = [System.Collections.Generic.List[object]]::new()
$script:Warnings   = [System.Collections.Generic.List[string]]::new()

$script:StartUtc = [DateTime]::UtcNow

# Variables explicitement initialisées pour être sûres sous StrictMode.
$script:SourceRoot   = $null
$script:PhysicalPath = $null
$script:RunId        = $null
$script:OutputDir    = $null
$script:ReportPath   = $null
$script:PythonFingerprint = $null
$script:AstResult    = $null

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

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop

    return [System.IO.Path]::GetFullPath(
        $resolved.Path
    )
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

    $separator = [System.IO.Path]::DirectorySeparatorChar

    if (-not $parentCanonical.EndsWith([string]$separator)) {
        $parentCanonical += $separator
    }

    return $childCanonical.StartsWith(
        $parentCanonical,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

# ============================================================================
# SHA-256
# ============================================================================

function Get-FileSha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $hashObject = Get-FileHash `
        -LiteralPath $Path `
        -Algorithm SHA256 `
        -ErrorAction Stop

    return $hashObject.Hash.ToLowerInvariant()
}

# ============================================================================
# STRICT JSON
# ============================================================================

function Read-JsonFileStrict {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Fichier JSON introuvable : $Path"
    }

    $raw = [System.IO.File]::ReadAllText(
        $Path,
        [System.Text.UTF8Encoding]::new($false)
    )

    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "Fichier JSON vide : $Path"
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
        throw "records.jsonl introuvable : $RecordsPath"
    }

    $normalizedTarget = $RelativePath.Replace('\','/').TrimStart('/')

    $lineNumber = 0

    foreach ($line in [System.IO.File]::ReadLines($RecordsPath)) {

        $lineNumber++

        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }

        try {
            $record = $line | ConvertFrom-Json -ErrorAction Stop
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

            if ($record.PSObject.Properties.Name -contains $propertyName) {

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
# SAFE SAMPLE
#
# IMPORTANT :
# On retourne un OBJET contenant le tableau.
# Cela empêche PowerShell de "déplier" le tableau dans le pipeline et
# d'introduire accidentellement une chaîne vide/scalar.
# ============================================================================

function Get-SafeTextSample {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $false)]
        [ValidateRange(1,10000)]
        [int]$MaxLines = 300
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Fichier absent pour échantillonnage : $Path"
    }

    $lines = [System.Collections.Generic.List[string]]::new()

    foreach ($line in [System.IO.File]::ReadLines($Path)) {

        # Même une ligne vide est une donnée physique valide.
        $lines.Add([string]$line)

        if ($lines.Count -ge $MaxLines) {
            break
        }
    }

    return [PSCustomObject]@{
        Lines = [string[]]$lines.ToArray()
        Count = $lines.Count
    }
}

# ============================================================================
# PYTHON FINGERPRINT
# ============================================================================

function Test-PythonFingerprint {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        [AllowEmptyCollection()]
        [AllowEmptyString()]
        [string[]]$Lines
    )

    if ($null -eq $Lines) {

        return [PSCustomObject]@{
            IsPythonLike = $false
            Score        = 0
            Evidence     = @()
            Reason       = 'NO_SAMPLE'
        }
    }

    $score = 0
    $evidence = [System.Collections.Generic.List[string]]::new()

    foreach ($line in $Lines) {

        if ($null -eq $line) {
            continue
        }

        $text = [string]$line

        if ($text -match '^\s*from\s+[A-Za-z0-9_.]+\s+import\s+') {
            $score += 3
            $evidence.Add('Python import: from ... import ...') | Out-Null
        }

        if ($text -match '^\s*import\s+[A-Za-z0-9_.]+') {
            $score += 2
            $evidence.Add('Python import: import ...') | Out-Null
        }

        if ($text -match '^\s*def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(') {
            $score += 3
            $evidence.Add('Python function: def ...') | Out-Null
        }

        if ($text -match '^\s*class\s+[A-Za-z_][A-Za-z0-9_]*\s*[:\(]') {
            $score += 2
            $evidence.Add('Python class declaration') | Out-Null
        }

        if ($text -match 'json\.dumps\s*\(') {
            $score += 3
            $evidence.Add('Python json.dumps(...)') | Out-Null
        }

        if ($text -match 'datetime\.utcnow\s*\(') {
            $score += 2
            $evidence.Add('Python datetime.utcnow(...)') | Out-Null
        }

        if ($text -match 'f["''].*\{[^}]+\}') {
            $score += 2
            $evidence.Add('Python f-string') | Out-Null
        }

        if ($text -match '^\s*for\s+\w+\s+in\s+') {
            $score += 2
            $evidence.Add('Python for ... in ...') | Out-Null
        }

        if ($text -match '^\s*if\s+.+:\s*$') {
            $score += 1
            $evidence.Add('Python if ...:') | Out-Null
        }
    }

    $uniqueEvidence = @(
        $evidence | Select-Object -Unique
    )

    return [PSCustomObject]@{
        IsPythonLike = ($score -ge 5)
        Score        = $score
        Evidence     = $uniqueEvidence
        Reason       = if ($score -ge 5) {
            'PYTHON_STRUCTURAL_FINGERPRINT'
        }
        else {
            'NO_STRONG_PYTHON_FINGERPRINT'
        }
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

    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref]$tokens,
        [ref]$errors
    )

    $errorObjects = @($errors)

    return [PSCustomObject]@{
        Valid      = ($errorObjects.Count -eq 0)
        ErrorCount = $errorObjects.Count
        Errors     = $errorObjects
    }
}

# ============================================================================
# FORENSIC OUTPUT
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
            -ErrorAction Stop | Out-Null
    }

    $dir = Join-Path $Root ("run_" + $RunId)

    if (-not (Test-Path -LiteralPath $dir -PathType Container)) {

        New-Item `
            -ItemType Directory `
            -Path $dir `
            -Force `
            -ErrorAction Stop | Out-Null
    }

    return $dir
}

# ============================================================================
# MAIN
# ============================================================================

try {

    Write-Section "E-ZZIO — FORENSIC EXTENSION TRUTH v$($script:EngineVersion)"

    Write-Host "Mode              : READ-ONLY / FORENSIC / FAIL-CLOSED"
    Write-Host "PointZeroDir      : $PointZeroDir"
    Write-Host "Target            : $Target"
    Write-Host "ForensicRoot      : $ForensicRoot"

    # ========================================================================
    # SG-00
    # ========================================================================

    Write-Section "SG-00 — PREFLIGHT"

    if (-not (Test-Path -LiteralPath $PointZeroDir -PathType Container)) {
        throw "Point Zero inexistant : $PointZeroDir"
    }

    Write-Pass "Point Zero existe"
    Add-GateResult `
        'SG-00_POINTZERO' `
        $true `
        'Point Zero présent'

    $manifestPath = Join-Path $PointZeroDir 'run_manifest.json'
    $recordsPath  = Join-Path $PointZeroDir 'records.jsonl'

    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Manifest absent : $manifestPath"
    }

    Write-Pass "Manifest présent"

    if (-not (Test-Path -LiteralPath $recordsPath -PathType Leaf)) {
        throw "Records absents : $recordsPath"
    }

    Write-Pass "Records présents"

    Add-GateResult `
        'SG-00_MANIFEST' `
        $true `
        'Manifest présent'

    Add-GateResult `
        'SG-00_RECORDS' `
        $true `
        'records.jsonl présent'

    # ========================================================================
    # SG-01
    # ========================================================================

    Write-Section "SG-01 — IDENTITÉ DU POINT ZERO"

    $manifest = Read-JsonFileStrict $manifestPath

    if (-not (
        $manifest.PSObject.Properties.Name -contains 'RootPathScanned'
    )) {
        throw "RootPathScanned absent du manifest."
    }

    $sourceRootRaw = [string]$manifest.RootPathScanned

    if ([string]::IsNullOrWhiteSpace($sourceRootRaw)) {
        throw "RootPathScanned est vide."
    }

    Write-Pass "RootPathScanned présent"

    if (-not (Test-Path -LiteralPath $sourceRootRaw -PathType Container)) {
        throw "Source Root inaccessible : $sourceRootRaw"
    }

    $script:SourceRoot = Resolve-CanonicalPath $sourceRootRaw

    Write-Host "Source Root live : $script:SourceRoot"

    Add-GateResult `
        'SG-01_ROOTPATHSCANNED' `
        $true `
        $script:SourceRoot

    # ========================================================================
    # SG-02
    # ========================================================================

    Write-Section "SG-02 — RÉSOLUTION PHYSIQUE"

    $targetNormalized =
        $Target.Replace('/','\').TrimStart('\')

    if ([string]::IsNullOrWhiteSpace($targetNormalized)) {
        throw "Target vide après normalisation."
    }

    $script:PhysicalPath = [System.IO.Path]::GetFullPath(
        (Join-Path $script:SourceRoot $targetNormalized)
    )

    Write-Host "PhysicalPath : $script:PhysicalPath"

    if (-not (Test-PathInside `
        -Child $script:PhysicalPath `
        -Parent $script:SourceRoot)) {

        throw "PATH TRAVERSAL : Target sort du SourceRoot."
    }

    Write-Pass "Target confinée dans SourceRoot"

    if (-not (Test-Path `
        -LiteralPath $script:PhysicalPath `
        -PathType Leaf)) {

        throw "Fichier physique absent : $script:PhysicalPath"
    }

    Write-Pass "Fichier physique présent"

    Add-GateResult `
        'SG-02_PHYSICAL_RESOLUTION' `
        $true `
        $script:PhysicalPath

    # ========================================================================
    # SG-03
    # ========================================================================

    Write-Section "SG-03 — IDENTITÉ PHYSIQUE / SHA-256"

    $fileInfo = Get-Item `
        -LiteralPath $script:PhysicalPath `
        -Force `
        -ErrorAction Stop

    $physicalHash = Get-FileSha256 $script:PhysicalPath

    Write-Host "Size       : $($fileInfo.Length) octets"
    Write-Host "SHA-256    : $physicalHash"
    Write-Host "LastWrite  : $($fileInfo.LastWriteTimeUtc.ToString('o'))"

    Add-GateResult `
        'SG-03_PHYSICAL_HASH' `
        $true `
        $physicalHash

    # ========================================================================
    # SG-04
    # ========================================================================

    Write-Section "SG-04 — CORRESPONDANCE POINT ZERO"

    $recordResult = Find-RecordForRelativePath `
        -RecordsPath $recordsPath `
        -RelativePath $targetNormalized

    if ($null -eq $recordResult) {
        throw "Aucun record Point Zero trouvé pour : $targetNormalized"
    }

    Write-Pass "Record trouvé à la ligne $($recordResult.LineNumber)"

    $record = $recordResult.Record
    $recordHash = $null

    foreach ($propertyName in @(
        'SHA256',
        'Sha256',
        'sha256',
        'Hash',
        'hash',
        'FileHash'
    )) {

        if ($record.PSObject.Properties.Name -contains $propertyName) {

            $candidateHash = [string]$record.$propertyName

            if (-not [string]::IsNullOrWhiteSpace($candidateHash)) {

                $recordHash = $candidateHash.ToLowerInvariant()
                break
            }
        }
    }

    if ([string]::IsNullOrWhiteSpace($recordHash)) {
        throw "SHA-256 absent du record Point Zero."
    }

    Write-Host "Record SHA-256 : $recordHash"

    if ($physicalHash -ne $recordHash) {

        throw `
            "HASH MISMATCH : physique=$physicalHash / PointZero=$recordHash"
    }

    Write-Pass "SHA-256 physique == SHA-256 Point Zero"

    Add-GateResult `
        'SG-04_HASH_PARITY' `
        $true `
        'SHA-256 identique'

    # ========================================================================
    # SG-05
    # ========================================================================

    Write-Section "SG-05 — VÉRITÉ DE L'EXTENSION"

    $extension =
        [System.IO.Path]::GetExtension(
            $script:PhysicalPath
        ).ToLowerInvariant()

    Write-Host "Extension : $extension"

    if ([string]::IsNullOrWhiteSpace($extension)) {
        throw "Le fichier ne possède aucune extension."
    }

    if ($extension -ne '.ps1') {
        throw "Target inattendue : extension $extension au lieu de .ps1"
    }

    Write-Pass "Extension .ps1 confirmée"

    Add-GateResult `
        'SG-05_EXTENSION' `
        $true `
        '.ps1'

    # ========================================================================
    # SG-06
    # ========================================================================

    Write-Section "SG-06 — FINGERPRINT DU CONTENU"

    $sampleObject = Get-SafeTextSample `
        -Path $script:PhysicalPath `
        -MaxLines 300

    if ($null -eq $sampleObject) {
        throw "Objet d'échantillon absent."
    }

    $sample = [string[]]$sampleObject.Lines
    $sampleCount = [int]$sampleObject.Count

    if ($sampleCount -eq 0) {

        Write-Fail "Fichier sans lignes physiques."

        Add-GateResult `
            'SG-06_SAMPLE' `
            $false `
            'EMPTY_SAMPLE'

        throw "Impossible d'effectuer le fingerprint : échantillon vide."
    }

    Write-Host "Lignes échantillonnées : $sampleCount"

    # Conversion explicite : aucune ambiguïté pipeline/scalar.
    $script:PythonFingerprint =
        Test-PythonFingerprint -Lines ([string[]]$sample)

    Write-Host ''
    Write-Host 'Python fingerprint :' -ForegroundColor Yellow
    Write-Host "  Score       : $($script:PythonFingerprint.Score)"
    Write-Host "  PythonLike  : $($script:PythonFingerprint.IsPythonLike)"
    Write-Host "  Reason      : $($script:PythonFingerprint.Reason)"

    if (@($script:PythonFingerprint.Evidence).Count -gt 0) {

        Write-Host '  Evidence :' -ForegroundColor DarkYellow

        foreach ($evidence in @($script:PythonFingerprint.Evidence)) {
            Write-Host "    - $evidence"
        }
    }

    Add-GateResult `
        'SG-06_SAMPLE' `
        $true `
        "$sampleCount lignes analysées"

    # ========================================================================
    # SG-07
    # ========================================================================

    Write-Section "SG-07 — POWERSHELL AST FORENSIC"

    $script:AstResult =
        Test-PowerShellAst $script:PhysicalPath

    Write-Host "AST Errors : $($script:AstResult.ErrorCount)"

    if ($script:AstResult.Valid) {

        Write-Pass "PowerShell AST valide"

        Add-GateResult `
            'SG-07_POWERSHELL_AST' `
            $true `
            '0 erreur AST'
    }
    else {

        Write-Fail `
            "PowerShell AST invalide : $($script:AstResult.ErrorCount) erreur(s)"

        foreach ($astError in @($script:AstResult.Errors)) {

            Write-Host ''

            Write-Host `
                "[AST] Ligne $($astError.Extent.StartLineNumber), colonne $($astError.Extent.StartColumnNumber)" `
                -ForegroundColor Red

            Write-Host `
                "      $($astError.Message)" `
                -ForegroundColor Red

            $astText = [string]$astError.Extent.Text

            if (-not [string]::IsNullOrWhiteSpace($astText)) {

                Write-Host `
                    "      Texte : $astText" `
                    -ForegroundColor DarkRed
            }
        }

        Add-GateResult `
            'SG-07_POWERSHELL_AST' `
            $false `
            "$($script:AstResult.ErrorCount) erreur(s) AST"

        # ====================================================================
        # SG-08 : DIAGNOSTIC STRUCTUREL
        # ====================================================================

        Write-Section "SG-08 — EXTENSION / CONTENU"

        if ($script:PythonFingerprint.IsPythonLike) {

            Write-Fail `
                'ABERRATION STRUCTURELLE : fichier .ps1 fortement identifié comme Python.'

            Add-GateResult `
                'SG-08_EXTENSION_CONTENT_PARITY' `
                $false `
                'PS1 contenant des marqueurs Python'

        }
        else {

            Write-Fail `
                'Fichier .ps1 avec AST invalide.'

            Add-GateResult `
                'SG-08_EXTENSION_CONTENT_PARITY' `
                $false `
                'PS1 avec AST invalide'
        }

        throw `
            "FAIL-CLOSED : le fichier .ps1 n'est pas un PowerShell syntaxiquement valide."
    }

    # ========================================================================
    # SG-08 — uniquement atteint si AST valide
    # ========================================================================

    Write-Section "SG-08 — EXTENSION / CONTENU"

    if ($script:PythonFingerprint.IsPythonLike) {

        Write-Fail `
            'Extension .ps1 incompatible avec le fingerprint Python.'

        Add-GateResult `
            'SG-08_EXTENSION_CONTENT_PARITY' `
            $false `
            'Python fingerprint détecté'

        throw `
            'FAIL-CLOSED : extension .ps1 incompatible avec contenu Python.'
    }

    Write-Pass "Aucun fingerprint Python fort détecté"

    Add-GateResult `
        'SG-08_EXTENSION_CONTENT_PARITY' `
        $true `
        'Pas de fingerprint Python fort'

    # ========================================================================
    # VERDICT
    # ========================================================================

    Write-Section "VERDICT FORENSIC"

    $failedGates = @(
        $script:GateResults |
            Where-Object { -not $_.Passed }
    )

    if ($failedGates.Count -gt 0) {

        Write-Host ''
        Write-Host 'FAIL-CLOSED' -ForegroundColor Red
        Write-Host ''
        Write-Host `
            "Gates échouées : $($failedGates.Count)" `
            -ForegroundColor Red

        foreach ($gate in $failedGates) {

            Write-Host `
                "  - $($gate.Gate) : $($gate.Detail)" `
                -ForegroundColor Red
        }

        $script:ExitCode = 1
    }
    else {

        Write-Host ''
        Write-Host `
            'CERTIFIED — EXTENSION / CONTENU COHÉRENTS' `
            -ForegroundColor Green

        Write-Host `
            'Toutes les gates sont PASS.' `
            -ForegroundColor Green

        $script:ExitCode = 0
    }
}
catch {

    $script:FatalError = $_
    $script:ExitCode = 1

    Write-Host ''
    Write-Host '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' `
        -ForegroundColor Red
    Write-Host ' E-ZZIO — FAIL-CLOSED' -ForegroundColor Red
    Write-Host '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' `
        -ForegroundColor Red
    Write-Host ''

    Write-Host `
        "ERROR : $($_.Exception.Message)" `
        -ForegroundColor Red

    Write-Host `
        "TYPE  : $($_.Exception.GetType().FullName)" `
        -ForegroundColor Red

    if ($_.InvocationInfo) {

        Write-Host ''
        Write-Host 'FORENSIC LOCATION' -ForegroundColor Yellow

        Write-Host "Script : $($_.InvocationInfo.ScriptName)"
        Write-Host "Line   : $($_.InvocationInfo.ScriptLineNumber)"
        Write-Host "Code   : $($_.InvocationInfo.Line)"
    }

    Write-Host ''
    Write-Host 'AUCUN CERTIFIED/FROZEN ÉMIS.' -ForegroundColor Red
    Write-Host 'AUCUNE MODIFICATION DU CORPUS.' -ForegroundColor Green
}

# ============================================================================
# FINALLY / REPORT
# ============================================================================

finally {

    try {

        # ------------------------------------------------------------
        # RunId
        # ------------------------------------------------------------

        if ([string]::IsNullOrWhiteSpace($PointZeroDir)) {
            throw 'PointZeroDir indisponible pour le rapport forensic.'
        }

        $script:RunId = Split-Path `
            -Leaf `
            ([System.IO.Path]::GetFullPath($PointZeroDir))

        # ------------------------------------------------------------
        # Output forensic hors corpus
        # ------------------------------------------------------------

        $outputRoot =
            Join-Path $ForensicRoot 'SemanticExtensionTruth'

        $script:OutputDir =
            Initialize-ForensicOutput `
                -Root $outputRoot `
                -RunId $script:RunId

        $script:ReportPath =
            Join-Path `
                $script:OutputDir `
                'extension_truth_report.json'

        # ------------------------------------------------------------
        # Failed gates
        # ------------------------------------------------------------

        $failedGatesForReport = @(
            $script:GateResults |
                Where-Object { -not $_.Passed }
        )

        # ------------------------------------------------------------
        # Fatal error
        # ------------------------------------------------------------

        $fatalForReport = $null

        if ($null -ne $script:FatalError) {

            $fatalForReport = [PSCustomObject]@{
                Type = $script:FatalError.Exception.GetType().FullName
                Message = $script:FatalError.Exception.Message

                ScriptName =
                    if ($script:FatalError.InvocationInfo) {
                        $script:FatalError.InvocationInfo.ScriptName
                    }
                    else {
                        $null
                    }

                ScriptLineNumber =
                    if ($script:FatalError.InvocationInfo) {
                        $script:FatalError.InvocationInfo.ScriptLineNumber
                    }
                    else {
                        $null
                    }

                Line =
                    if ($script:FatalError.InvocationInfo) {
                        $script:FatalError.InvocationInfo.Line
                    }
                    else {
                        $null
                    }
            }
        }

        # ------------------------------------------------------------
        # Report
        # ------------------------------------------------------------

        $finishedUtc = [DateTime]::UtcNow

        $report = [PSCustomObject]@{

            Engine = [PSCustomObject]@{
                Name =
                    'E-ZZIO — FORENSIC EXTENSION TRUTH'

                Version =
                    $script:EngineVersion

                Mode =
                    'READ-ONLY / FORENSIC / FAIL-CLOSED'
            }

            Execution = [PSCustomObject]@{
                StartedAtUtc =
                    $script:StartUtc.ToString('o')

                FinishedAtUtc =
                    $finishedUtc.ToString('o')

                ExitCode =
                    $script:ExitCode
            }

            Inputs = [PSCustomObject]@{
                PointZeroDir =
                    $PointZeroDir

                Target =
                    $Target

                SourceRoot =
                    $script:SourceRoot

                PhysicalPath =
                    $script:PhysicalPath
            }

            PhysicalEvidence = [PSCustomObject]@{
                Extension =
                    if ($script:PhysicalPath) {
                        [System.IO.Path]::GetExtension(
                            $script:PhysicalPath
                        ).ToLowerInvariant()
                    }
                    else {
                        $null
                    }

                SHA256 =
                    if ($script:PhysicalPath -and
                        (Test-Path -LiteralPath $script:PhysicalPath -PathType Leaf)) {

                        try {
                            Get-FileSha256 $script:PhysicalPath
                        }
                        catch {
                            $null
                        }
                    }
                    else {
                        $null
                    }

                SizeBytes =
                    if ($script:PhysicalPath -and
                        (Test-Path -LiteralPath $script:PhysicalPath -PathType Leaf)) {

                        try {
                            (Get-Item -LiteralPath $script:PhysicalPath -Force).Length
                        }
                        catch {
                            $null
                        }
                    }
                    else {
                        $null
                    }
            }

            PythonFingerprint =
                $script:PythonFingerprint

            PowerShellAst =
                if ($null -ne $script:AstResult) {

                    [PSCustomObject]@{
                        Valid =
                            $script:AstResult.Valid

                        ErrorCount =
                            $script:AstResult.ErrorCount

                        Errors = @(
                            foreach ($err in @($script:AstResult.Errors)) {

                                [PSCustomObject]@{
                                    Message =
                                        $err.Message

                                    StartLine =
                                        $err.Extent.StartLineNumber

                                    StartColumn =
                                        $err.Extent.StartColumnNumber

                                    EndLine =
                                        $err.Extent.EndLineNumber

                                    EndColumn =
                                        $err.Extent.EndColumnNumber

                                    Text =
                                        [string]$err.Extent.Text
                                }
                            }
                        )
                    }
                }
                else {
                    $null
                }

            Gates = @(
                $script:GateResults
            )

            FailedGates = @(
                $failedGatesForReport
            )

            Warnings = @(
                $script:Warnings
            )

            FatalError =
                $fatalForReport

            Verdict =
                if ($script:ExitCode -eq 0) {
                    'CERTIFIED'
                }
                else {
                    'FAIL_CLOSED'
                }

            Mutation = [PSCustomObject]@{
                CorpusModified =
                    $false

                PointZeroModified =
                    $false

                RenamePerformed =
                    $false

                DestructiveActionPerformed =
                    $false
            }
        }

        $json = $report |
            ConvertTo-Json -Depth 20

        [System.IO.File]::WriteAllText(
            $script:ReportPath,
            $json,
            [System.Text.UTF8Encoding]::new($false)
        )

        Write-Host ''
        Write-Host '==============================================================================' `
            -ForegroundColor DarkCyan
        Write-Host ' FORENSIC REPORT' -ForegroundColor DarkCyan
        Write-Host '==============================================================================' `
            -ForegroundColor DarkCyan

        Write-Host `
            "Rapport : $script:ReportPath" `
            -ForegroundColor DarkGray

    }
    catch {

        Write-Host ''
        Write-Host `
            '[CRITICAL] Impossible d''écrire le rapport forensic.' `
            -ForegroundColor Red

        Write-Host `
            $_.Exception.Message `
            -ForegroundColor Red

        $script:ExitCode = 1
    }

    # ========================================================================
    # FINAL CONSOLE STATE
    # ========================================================================

    Write-Host ''
    Write-Host '==============================================================================' `
        -ForegroundColor Cyan

    if ($script:ExitCode -eq 0) {

        Write-Host `
            ' E-ZZIO — FORENSIC EXTENSION TRUTH : CERTIFIED' `
            -ForegroundColor Green
    }
    else {

        Write-Host `
            ' E-ZZIO — FORENSIC EXTENSION TRUTH : FAIL-CLOSED' `
            -ForegroundColor Red
    }

    Write-Host '==============================================================================' `
        -ForegroundColor Cyan

    Write-Host ''
    Write-Host 'Corpus : NON MODIFIÉ' -ForegroundColor Green
    Write-Host 'Point Zero : NON MODIFIÉ' -ForegroundColor Green
    Write-Host 'Renommage automatique : AUCUN' -ForegroundColor Green

    Write-Host ''
    Write-Host "ExitCode logique : $script:ExitCode" -ForegroundColor Yellow
    Write-Host ''

    if ($PauseOnExit) {

        Read-Host 'Appuyez sur Entrée pour fermer'
    }
}
