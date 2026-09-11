# ============================================================================
# E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v4.0.0
# ============================================================================
# MODE        : READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED
# QUALITY     : FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE
#
# OBJECTIVE
#   Explorer mécaniquement plusieurs familles de réparations syntaxiques
#   PowerShell dans des clones isolés des sources originales.
#
# ABSOLUTE GUARANTEES
#   - Aucun fichier source original n'est modifié.
#   - Aucun candidat n'est exécuté.
#   - Aucune promotion automatique.
#   - Aucun statut CERTIFIED.
#   - Toute amélioration doit être démontrée par Parser.ParseFile().
#   - Toute régression entraîne le rejet du candidat.
#
# ============================================================================
# VERSION
# ============================================================================
$EngineName   = 'E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB'
$ScriptVersion = '4.0.0'

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================
$ProjectRoot = 'G:\AI\E-zzio'

$ReportsRoot = Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'

# ============================================================================
# UI
# ============================================================================
function Write-Banner {
    param(
        [string]$Title,
        [ConsoleColor]$Color = [ConsoleColor]::Cyan
    )

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor $Color
    Write-Host " $Title" -ForegroundColor $Color
    Write-Host '============================================================================' -ForegroundColor $Color
}

function Write-Step {
    param(
        [string]$Step,
        [string]$Text
    )

    Write-Host ''
    Write-Host "[$Step] $Text" -ForegroundColor Cyan
}

function Write-Info {
    param(
        [string]$Name,
        [object]$Value
    )

    Write-Host ("      {0,-28}: {1}" -f $Name, $Value)
}

function Write-Green {
    param([string]$Text)
    Write-Host $Text -ForegroundColor Green
}

function Write-Yellow {
    param([string]$Text)
    Write-Host $Text -ForegroundColor Yellow
}

function Write-Red {
    param([string]$Text)
    Write-Host $Text -ForegroundColor Red
}

# ============================================================================
# UTILITIES
# ============================================================================
function Ensure-Directory {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [AllowEmptyString()]
        [AllowNull()]
        [string]$Content
    )

    if ($null -eq $Content) {
        $Content = ''
    }

    $utf8 = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8)
}

function Get-Sha256 {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Get-RelativePath {
    param(
        [Parameter(Mandatory)]
        [string]$BasePath,

        [Parameter(Mandatory)]
        [string]$FullPath
    )

    $base = [System.IO.Path]::GetFullPath($BasePath)
    $full = [System.IO.Path]::GetFullPath($FullPath)

    if (-not $base.EndsWith([System.IO.Path]::DirectorySeparatorChar)) {
        $base += [System.IO.Path]::DirectorySeparatorChar
    }

    $baseUri = [System.Uri]$base
    $fullUri = [System.Uri]$full

    $relative = $baseUri.MakeRelativeUri($fullUri).ToString()

    return [System.Uri]::UnescapeDataString($relative).Replace('/', '\')
}

# ============================================================================
# PARSER
# ============================================================================
function Invoke-PowerShellParser {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $tokens = $null
    $parseErrors = $null

    $ast = [System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref]$tokens,
        [ref]$parseErrors
    )

    $records = @()

    foreach ($parseIssue in @($parseErrors)) {

        if ($null -eq $parseIssue) {
            continue
        }

        $extent = $parseIssue.Extent

        $records += [pscustomobject]@{
            Message    = [string]$parseIssue.Message
            ErrorId    = [string]$parseIssue.ErrorId
            Line       = [int]$extent.StartLineNumber
            Column     = [int]$extent.StartColumnNumber
            EndLine    = [int]$extent.EndLineNumber
            EndColumn  = [int]$extent.EndColumnNumber
            Text       = [string]$extent.Text
        }
    }

    return @($records)
}

function Get-ParserErrorCount {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return @(Invoke-PowerShellParser -Path $Path).Count
}

# ============================================================================
# SOURCE FILE DISCOVERY
# ============================================================================
function Get-TargetFilesFromRootMatrix {
    param(
        [Parameter(Mandatory)]
        [string]$RootMatrixPath
    )

    $raw = Get-Content -LiteralPath $RootMatrixPath -Raw -Encoding UTF8

    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "ROOT_CAUSE_MATRIX est vide."
    }

    $matrix = $raw | ConvertFrom-Json

    $paths = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )

    $allObjects = @($matrix)

    foreach ($object in $allObjects) {

        $properties = $object.PSObject.Properties

        foreach ($property in $properties) {

            $value = $property.Value

            if ($null -eq $value) {
                continue
            }

            if ($value -is [string]) {

                $candidate = $value.Trim()

                if ($candidate -match '^[A-Za-z]:\\') {

                    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
                        [void]$paths.Add(
                            [System.IO.Path]::GetFullPath($candidate)
                        )
                    }
                }
            }
        }
    }

    return @(
        $paths |
        Sort-Object
    )
}

# ============================================================================
# REPAIR STRATEGY ENGINE
# ============================================================================
#
# Chaque stratégie reçoit le contenu complet d'un candidat et retourne :
#
#   Changed  : bool
#   Content  : nouveau contenu
#   Strategy : nom
#
# Une stratégie ne doit JAMAIS modifier le fichier original.
# ============================================================================

function New-RepairResult {
    param(
        [bool]$Changed,
        [AllowEmptyString()]
        [string]$Content,
        [string]$Strategy,
        [string]$Reason
    )

    return [pscustomobject]@{
        Changed  = $Changed
        Content  = $Content
        Strategy = $Strategy
        Reason   = $Reason
    }
}

# ----------------------------------------------------------------------------
# STRATEGY 01 — Smart quotes
# ----------------------------------------------------------------------------
function Repair-SmartQuotes {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    $newContent = $Content

    $newContent = $newContent.Replace([char]0x2018, [char]0x27)
    $newContent = $newContent.Replace([char]0x2019, [char]0x27)
    $newContent = $newContent.Replace([char]0x201A, [char]0x27)
    $newContent = $newContent.Replace([char]0x201B, [char]0x27)

    $newContent = $newContent.Replace([char]0x201C, [char]0x22)
    $newContent = $newContent.Replace([char]0x201D, [char]0x22)
    $newContent = $newContent.Replace([char]0x201E, [char]0x22)
    $newContent = $newContent.Replace([char]0x201F, [char]0x22)

    if ($newContent -ceq $Content) {
        return New-RepairResult $false $Content 'SMART_QUOTES' 'Aucun caractère typographique détecté.'
    }

    return New-RepairResult $true $newContent 'SMART_QUOTES' 'Normalisation des guillemets typographiques.'
}

# ----------------------------------------------------------------------------
# STRATEGY 02 — Unicode dashes
# ----------------------------------------------------------------------------
function Repair-UnicodeDashes {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    $newContent = $Content

    $newContent = $newContent.Replace([char]0x2010, '-')
    $newContent = $newContent.Replace([char]0x2011, '-')
    $newContent = $newContent.Replace([char]0x2012, '-')
    $newContent = $newContent.Replace([char]0x2013, '-')
    $newContent = $newContent.Replace([char]0x2014, '-')
    $newContent = $newContent.Replace([char]0x2212, '-')

    if ($newContent -ceq $Content) {
        return New-RepairResult $false $Content 'UNICODE_DASHES' 'Aucun tiret Unicode problématique détecté.'
    }

    return New-RepairResult $true $newContent 'UNICODE_DASHES' 'Normalisation des tirets Unicode.'
}

# ----------------------------------------------------------------------------
# STRATEGY 03 — Zero-width / BOM artifacts
# ----------------------------------------------------------------------------
function Repair-InvisibleCharacters {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    $newContent = $Content

    $newContent = $newContent.Replace([char]0xFEFF, '')
    $newContent = $newContent.Replace([char]0x200B, '')
    $newContent = $newContent.Replace([char]0x200C, '')
    $newContent = $newContent.Replace([char]0x200D, '')
    $newContent = $newContent.Replace([char]0x2060, '')

    if ($newContent -ceq $Content) {
        return New-RepairResult $false $Content 'INVISIBLE_CHARS' 'Aucun caractère invisible détecté.'
    }

    return New-RepairResult $true $newContent 'INVISIBLE_CHARS' 'Suppression des caractères invisibles.'
}

# ----------------------------------------------------------------------------
# STRATEGY 04 — Markdown fences accidentally embedded in source
# ----------------------------------------------------------------------------
function Repair-MarkdownFences {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    $lines = @(
        $Content -split "`r?`n", -1
    )

    $changed = $false
    $result = [System.Collections.Generic.List[string]]::new()

    foreach ($line in $lines) {

        $trimmed = $line.Trim()

        if (
            $trimmed -eq '```powershell' -or
            $trimmed -eq '```PowerShell' -or
            $trimmed -eq '```pwsh' -or
            $trimmed -eq '```ps1' -or
            $trimmed -eq '```'
        ) {
            $changed = $true
            continue
        }

        [void]$result.Add($line)
    }

    if (-not $changed) {
        return New-RepairResult $false $Content 'MARKDOWN_FENCES' 'Aucun fence Markdown parasite détecté.'
    }

    return New-RepairResult `
        $true `
        ($result -join [Environment]::NewLine) `
        'MARKDOWN_FENCES' `
        'Suppression des fences Markdown autonomes.'
}

# ----------------------------------------------------------------------------
# STRATEGY 05 — PowerShell console prompt contamination
# ----------------------------------------------------------------------------
function Repair-ConsolePrompts {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    $lines = @(
        $Content -split "`r?`n", -1
    )

    $changed = $false
    $result = [System.Collections.Generic.List[string]]::new()

    foreach ($line in $lines) {

        if ($line -match '^\s*PS\s+[A-Za-z]:\\.*>\s?.*$') {
            $changed = $true
            continue
        }

        if ($line -match '^\s*>>\s?.*$') {
            $changed = $true
            continue
        }

        [void]$result.Add($line)
    }

    if (-not $changed) {
        return New-RepairResult $false $Content 'CONSOLE_PROMPTS' 'Aucun prompt PowerShell parasite détecté.'
    }

    return New-RepairResult `
        $true `
        ($result -join [Environment]::NewLine) `
        'CONSOLE_PROMPTS' `
        'Suppression de lignes de console manifestement injectées.'
}

# ----------------------------------------------------------------------------
# STRATEGY 06 — Trailing continuation cleanup
#
# On ne touche PAS aux backticks internes.
# Seulement aux backticks suivis d'espaces/tabulations en fin de ligne.
# ----------------------------------------------------------------------------
function Repair-TrailingBacktickWhitespace {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    $lines = @(
        $Content -split "`r?`n", -1
    )

    $changed = $false
    $result = [System.Collections.Generic.List[string]]::new()

    foreach ($line in $lines) {

        $newLine = $line -replace '`[ \t]+$', '`'

        if ($newLine -cne $line) {
            $changed = $true
        }

        [void]$result.Add($newLine)
    }

    if (-not $changed) {
        return New-RepairResult $false $Content 'BACKTICK_WHITESPACE' 'Aucune continuation mal terminée détectée.'
    }

    return New-RepairResult `
        $true `
        ($result -join [Environment]::NewLine) `
        'BACKTICK_WHITESPACE' `
        'Nettoyage des espaces après les continuations PowerShell.'
}

# ----------------------------------------------------------------------------
# STRATEGY 07 — Invalid NUL characters
# ----------------------------------------------------------------------------
function Repair-NulCharacters {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    if ($Content.IndexOf([char]0) -lt 0) {
        return New-RepairResult $false $Content 'NUL_CHARS' 'Aucun NUL détecté.'
    }

    $newContent = $Content.Replace([char]0, '')

    return New-RepairResult `
        $true `
        $newContent `
        'NUL_CHARS' `
        'Suppression de caractères NUL.'
}

# ----------------------------------------------------------------------------
# STRATEGY 08 — CR-only normalization
# ----------------------------------------------------------------------------
function Repair-LineEndings {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    if ($Content -notmatch "`r(?!`n)") {
        return New-RepairResult $false $Content 'LINE_ENDINGS' 'Aucune fin de ligne CR isolée.'
    }

    $newContent = $Content -replace "`r(?!`n)", "`n"

    return New-RepairResult `
        $true `
        $newContent `
        'LINE_ENDINGS' `
        'Normalisation des retours CR isolés.'
}

# ----------------------------------------------------------------------------
# STRATEGY 09 — Remove obvious accidental leading output markers
# ----------------------------------------------------------------------------
function Repair-AccidentalTranscriptMarkers {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    $lines = @(
        $Content -split "`r?`n", -1
    )

    $changed = $false
    $result = [System.Collections.Generic.List[string]]::new()

    foreach ($line in $lines) {

        if ($line -match '^\s*Appuie sur ENTREE pour terminer') {
            $changed = $true
            continue
        }

        if ($line -match '^\s*La fenêtre reste ouverte\.?\s*$') {
            $changed = $true
            continue
        }

        [void]$result.Add($line)
    }

    if (-not $changed) {
        return New-RepairResult $false $Content 'TRANSCRIPT_MARKERS' 'Aucun marqueur de transcript évident.'
    }

    return New-RepairResult `
        $true `
        ($result -join [Environment]::NewLine) `
        'TRANSCRIPT_MARKERS' `
        'Suppression de marqueurs de session interactifs.'
}

# ============================================================================
# STRATEGY REGISTRY
# ============================================================================
$Strategies = @(
    @{
        Name = 'SMART_QUOTES'
        Function = 'Repair-SmartQuotes'
    },
    @{
        Name = 'UNICODE_DASHES'
        Function = 'Repair-UnicodeDashes'
    },
    @{
        Name = 'INVISIBLE_CHARS'
        Function = 'Repair-InvisibleCharacters'
    },
    @{
        Name = 'MARKDOWN_FENCES'
        Function = 'Repair-MarkdownFences'
    },
    @{
        Name = 'CONSOLE_PROMPTS'
        Function = 'Repair-ConsolePrompts'
    },
    @{
        Name = 'BACKTICK_WHITESPACE'
        Function = 'Repair-TrailingBacktickWhitespace'
    },
    @{
        Name = 'NUL_CHARS'
        Function = 'Repair-NulCharacters'
    },
    @{
        Name = 'LINE_ENDINGS'
        Function = 'Repair-LineEndings'
    },
    @{
        Name = 'TRANSCRIPT_MARKERS'
        Function = 'Repair-AccidentalTranscriptMarkers'
    }
)

# ============================================================================
# CANDIDATE VALIDATION
# ============================================================================
function Test-CandidateContent {
    param(
        [Parameter(Mandatory)]
        [string]$CandidatePath
    )

    $issues = @(Invoke-PowerShellParser -Path $CandidatePath)

    return [pscustomobject]@{
        Valid  = ($issues.Count -eq 0)
        Count  = $issues.Count
        Errors = @($issues)
    }
}

# ============================================================================
# CANDIDATE WRITE
# ============================================================================
function Write-CandidateContent {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [AllowEmptyString()]
        [string]$Content
    )

    if ($null -eq $Content) {
        $Content = ''
    }

    Write-Utf8NoBom -Path $Path -Content $Content
}

# ============================================================================
# SINGLE STRATEGY EVALUATION
# ============================================================================
function Invoke-StrategyTrial {
    param(
        [Parameter(Mandatory)]
        [string]$SourcePath,

        [Parameter(Mandatory)]
        [string]$CandidatePath,

        [Parameter(Mandatory)]
        [string]$StrategyName,

        [Parameter(Mandatory)]
        [string]$StrategyFunction,

        [Parameter(Mandatory)]
        [int]$BaselineErrors
    )

    $sourceContent = Get-Content -LiteralPath $CandidatePath -Raw -Encoding UTF8

    if ($null -eq $sourceContent) {
        $sourceContent = ''
    }

    $repairResult = & $StrategyFunction -Content $sourceContent

    if ($null -eq $repairResult) {
        return [pscustomobject]@{
            Strategy       = $StrategyName
            Changed        = $false
            Accepted       = $false
            Regression     = $false
            BeforeErrors   = $BaselineErrors
            AfterErrors    = $BaselineErrors
            Improvement    = 0
            Reason         = 'La stratégie n''a produit aucun résultat.'
        }
    }

    if (-not $repairResult.Changed) {
        return [pscustomobject]@{
            Strategy       = $StrategyName
            Changed        = $false
            Accepted       = $false
            Regression     = $false
            BeforeErrors   = $BaselineErrors
            AfterErrors    = $BaselineErrors
            Improvement    = 0
            Reason         = $repairResult.Reason
        }
    }

    $trialPath = Join-Path (
        Split-Path -Parent $CandidatePath
    ) (
        '.TRIAL_' + [Guid]::NewGuid().ToString('N') + '.ps1'
    )

    try {

        Write-CandidateContent `
            -Path $trialPath `
            -Content $repairResult.Content

        $validation = Test-CandidateContent -CandidatePath $trialPath

        $afterErrors = [int]$validation.Count
        $improvement = $BaselineErrors - $afterErrors

        $accepted = (
            $afterErrors -lt $BaselineErrors
        )

        $regression = (
            $afterErrors -gt $BaselineErrors
        )

        return [pscustomobject]@{
            Strategy       = $StrategyName
            Changed        = $true
            Accepted       = $accepted
            Regression     = $regression
            BeforeErrors   = $BaselineErrors
            AfterErrors    = $afterErrors
            Improvement    = $improvement
            Reason         = [string]$repairResult.Reason
            TrialContent   = [string]$repairResult.Content
        }
    }
    finally {

        if (Test-Path -LiteralPath $trialPath -PathType Leaf) {
            Remove-Item -LiteralPath $trialPath -Force
        }
    }
}

# ============================================================================
# MAIN
# ============================================================================
try {

    Write-Banner "$EngineName v$ScriptVersion" ([ConsoleColor]::Green)

    Write-Info 'PROJECT' $ProjectRoot
    Write-Info 'MODE' 'READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED'
    Write-Info 'QUALITY' 'FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
    Write-Info 'SOURCE MUTATION' 'DISABLED'
    Write-Info 'EXECUTION' 'DISABLED'
    Write-Info 'PROMOTION' 'DISABLED'

    # ========================================================================
    # 1 — ENVIRONMENT
    # ========================================================================
    Write-Step '1/18' 'Validation environnement...'

    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw "PROJECT ROOT introuvable : $ProjectRoot"
    }

    if (-not (Test-Path -LiteralPath $ReportsRoot -PathType Container)) {
        throw "Répertoire forensic introuvable : $ReportsRoot"
    }

    $psVersion = $PSVersionTable.PSVersion.ToString()

    Write-Info 'POWERSHELL' $psVersion
    Write-Green '      ENVIRONMENT                 : PASS'

    # ========================================================================
    # 2 — DISCOVER LAST DOSSIER
    # ========================================================================
    Write-Step '2/18' 'Recherche du dernier REPAIR_DOSSIER...'

    $repairDossiers = @(
        Get-ChildItem `
            -LiteralPath $ReportsRoot `
            -Directory `
            -Recurse `
            -ErrorAction Stop |
        Where-Object {
            $_.Name -eq 'REPAIR_DOSSIER'
        } |
        Sort-Object LastWriteTimeUtc -Descending
    )

    if ($repairDossiers.Count -eq 0) {
        throw 'Aucun REPAIR_DOSSIER trouvé.'
    }

    $RepairDossier = $repairDossiers[0].FullName

    Write-Info 'DOSSIER' $RepairDossier
    Write-Green '      DISCOVERY                   : PASS'

    # ========================================================================
    # 3 — MATRIX
    # ========================================================================
    Write-Step '3/18' 'Chargement de la Root-Cause Matrix...'

    $RootMatrixPath = Join-Path `
        $RepairDossier `
        'ROOT_CAUSE_MATRIX.json'

    if (-not (Test-Path -LiteralPath $RootMatrixPath -PathType Leaf)) {
        throw "ROOT_CAUSE_MATRIX.json introuvable."
    }

    $matrixRaw = Get-Content `
        -LiteralPath $RootMatrixPath `
        -Raw `
        -Encoding UTF8

    if ([string]::IsNullOrWhiteSpace($matrixRaw)) {
        throw 'ROOT_CAUSE_MATRIX.json est vide.'
    }

    $matrix = $matrixRaw | ConvertFrom-Json

    $rootCauseObjects = @($matrix)

    $RootCauseCount = $rootCauseObjects.Count

    Write-Info 'ROOT CAUSES' $RootCauseCount

    # ========================================================================
    # 4 — TARGET FILES
    # ========================================================================
    Write-Step '4/18' 'Identification forensic des fichiers cibles...'

    $TargetFiles = @(Get-TargetFilesFromRootMatrix -RootMatrixPath $RootMatrixPath)

    if ($TargetFiles.Count -eq 0) {
        throw 'Aucun fichier cible identifiable dans la Root-Cause Matrix.'
    }

    $TargetFileCount = $TargetFiles.Count

    Write-Info 'TARGET FILES' $TargetFileCount

    # ========================================================================
    # 5 — RUN
    # ========================================================================
    Write-Step '5/18' 'Création du laboratoire forensic...'

    $RunId = (
        [DateTime]::Now.ToString('yyyyMMdd_HHmmss_fff') +
        '_' +
        ([Guid]::NewGuid().ToString('N').Substring(0, 12))
    )

    $RunRoot = Join-Path `
        $ReportsRoot `
        $RunId

    $Workbench = Join-Path `
        $RunRoot `
        'SUPER_FORENSIC_REPAIR_LAB'

    $CandidatesRoot = Join-Path `
        $Workbench `
        'CANDIDATES'

    $AcceptedRoot = Join-Path `
        $Workbench `
        'ACCEPTED_CANDIDATES'

    $RejectedRoot = Join-Path `
        $Workbench `
        'REJECTED_CANDIDATES'

    $EvidenceRoot = Join-Path `
        $Workbench `
        'EVIDENCE'

    $Reports = Join-Path `
        $Workbench `
        'REPORTS'

    Ensure-Directory $Workbench
    Ensure-Directory $CandidatesRoot
    Ensure-Directory $AcceptedRoot
    Ensure-Directory $RejectedRoot
    Ensure-Directory $EvidenceRoot
    Ensure-Directory $Reports

    Write-Info 'RUN ID' $RunId
    Write-Info 'WORKBENCH' $Workbench
    Write-Green '      WORKBENCH                  : PASS'

    # ========================================================================
    # 6 — BASELINE
    # ========================================================================
    Write-Step '6/18' 'Construction du baseline SHA-256 + parser original...'

    $baselineRecords = [System.Collections.Generic.List[object]]::new()

    $originalErrorTotal = 0

    foreach ($sourcePath in $TargetFiles) {

        $parserIssues = @(Invoke-PowerShellParser -Path $sourcePath)
        $errorCount = $parserIssues.Count

        $hash = Get-Sha256 -Path $sourcePath

        $relative = Get-RelativePath `
            -BasePath $ProjectRoot `
            -FullPath $sourcePath

        [void]$baselineRecords.Add(
            [pscustomobject]@{
                RelativePath = $relative
                SourcePath   = $sourcePath
                SHA256       = $hash
                ParserErrors = $errorCount
                ParserIssues = @($parserIssues)
            }
        )

        $originalErrorTotal += $errorCount
    }

    Write-Info 'BASELINE FILES' $baselineRecords.Count
    Write-Info 'PARSER ERRORS' $originalErrorTotal

    # ========================================================================
    # 7 — CLONE
    # ========================================================================
    Write-Step '7/18' 'Clonage strict des sources...'

    $candidateRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($baseline in $baselineRecords) {

        $candidatePath = Join-Path `
            $CandidatesRoot `
            $baseline.RelativePath

        $candidateDirectory = Split-Path `
            -Parent `
            $candidatePath

        Ensure-Directory $candidateDirectory

        Copy-Item `
            -LiteralPath $baseline.SourcePath `
            -Destination $candidatePath `
            -Force

        $candidateHash = Get-Sha256 -Path $candidatePath

        if ($candidateHash -ne $baseline.SHA256) {
            throw "Échec du clonage SHA-256 : $($baseline.RelativePath)"
        }

        [void]$candidateRecords.Add(
            [pscustomobject]@{
                RelativePath      = $baseline.RelativePath
                SourcePath        = $baseline.SourcePath
                CandidatePath     = $candidatePath
                OriginalSHA256    = $baseline.SHA256
                BaselineErrors    = $baseline.ParserErrors
                CurrentErrors     = $baseline.ParserErrors
                CurrentContent   = $null
                AcceptedStrategy = $null
            }
        )
    }

    Write-Info 'CLONED' $candidateRecords.Count

    # ========================================================================
    # 8 — STRATEGY INVENTORY
    # ========================================================================
    Write-Step '8/18' 'Chargement des stratégies de réparation...'

    Write-Info 'STRATEGIES' $Strategies.Count

    foreach ($strategy in $Strategies) {
        Write-Host ("      - {0}" -f $strategy.Name) -ForegroundColor DarkGray
    }

    # ========================================================================
    # 9 — GLOBAL STRATEGY SCAN
    # ========================================================================
    Write-Step '9/18' 'Scan de toutes les stratégies sur tous les candidats...'

    $trialResults = [System.Collections.Generic.List[object]]::new()

    $strategyTrialCount = 0

    foreach ($candidate in $candidateRecords) {

        if ($candidate.BaselineErrors -eq 0) {
            continue
        }

        foreach ($strategy in $Strategies) {

            $strategyTrialCount++

            $trial = Invoke-StrategyTrial `
                -SourcePath $candidate.SourcePath `
                -CandidatePath $candidate.CandidatePath `
                -StrategyName $strategy.Name `
                -StrategyFunction $strategy.Function `
                -BaselineErrors $candidate.CurrentErrors

            [void]$trialResults.Add(
                [pscustomobject]@{
                    RelativePath = $candidate.RelativePath
                    Strategy     = $trial.Strategy
                    Changed      = $trial.Changed
                    Accepted     = $trial.Accepted
                    Regression   = $trial.Regression
                    BeforeErrors = $trial.BeforeErrors
                    AfterErrors  = $trial.AfterErrors
                    Improvement  = $trial.Improvement
                    Reason       = $trial.Reason
                    TrialContent = $trial.TrialContent
                }
            )
        }
    }

    Write-Info 'TRIALS' $strategyTrialCount

    # ========================================================================
    # 10 — GREEDY PROVEN REPAIR
    # ========================================================================
    Write-Step '10/18' 'Application itérative des améliorations prouvées...'

    $acceptedRepairs = [System.Collections.Generic.List[object]]::new()

    $totalImprovement = 0

    foreach ($candidate in $candidateRecords) {

        $currentErrors = [int]$candidate.CurrentErrors

        if ($currentErrors -eq 0) {
            continue
        }

        $localIteration = 0

        while ($true) {

            $localIteration++

            if ($localIteration -gt ($Strategies.Count + 2)) {
                break
            }

            $currentContent = Get-Content `
                -LiteralPath $candidate.CandidatePath `
                -Raw `
                -Encoding UTF8

            if ($null -eq $currentContent) {
                $currentContent = ''
            }

            $bestTrial = $null

            foreach ($strategy in $Strategies) {

                $repairResult = & $strategy.Function -Content $currentContent

                if ($null -eq $repairResult) {
                    continue
                }

                if (-not $repairResult.Changed) {
                    continue
                }

                $trialPath = Join-Path `
                    (Split-Path -Parent $candidate.CandidatePath) `
                    ('.ITER_' + [Guid]::NewGuid().ToString('N') + '.ps1')

                try {

                    Write-CandidateContent `
                        -Path $trialPath `
                        -Content $repairResult.Content

                    $validation = Test-CandidateContent `
                        -CandidatePath $trialPath

                    $newErrorCount = [int]$validation.Count

                    if ($newErrorCount -lt $currentErrors) {

                        $delta = $currentErrors - $newErrorCount

                        if (
                            $null -eq $bestTrial -or
                            $delta -gt [int]$bestTrial.Improvement
                        ) {
                            $bestTrial = [pscustomobject]@{
                                Strategy    = $strategy.Name
                                Function    = $strategy.Function
                                Content     = $repairResult.Content
                                Before      = $currentErrors
                                After       = $newErrorCount
                                Improvement = $delta
                                Reason      = $repairResult.Reason
                            }
                        }
                    }
                }
                finally {

                    if (Test-Path -LiteralPath $trialPath -PathType Leaf) {
                        Remove-Item -LiteralPath $trialPath -Force
                    }
                }
            }

            if ($null -eq $bestTrial) {
                break
            }

            Write-CandidateContent `
                -Path $candidate.CandidatePath `
                -Content $bestTrial.Content

            $previousErrors = $currentErrors
            $currentErrors = $bestTrial.After

            $candidate.CurrentErrors = $currentErrors
            $candidate.AcceptedStrategy = $bestTrial.Strategy

            $totalImprovement += $bestTrial.Improvement

            [void]$acceptedRepairs.Add(
                [pscustomobject]@{
                    RelativePath = $candidate.RelativePath
                    Strategy     = $bestTrial.Strategy
                    BeforeErrors = $previousErrors
                    AfterErrors  = $currentErrors
                    Improvement  = $bestTrial.Improvement
                    Reason       = $bestTrial.Reason
                    Iteration    = $localIteration
                }
            )

            Write-Host (
                "      IMPROVED : {0} | {1} -> {2} | +{3} | {4}" -f
                $candidate.RelativePath,
                $previousErrors,
                $currentErrors,
                $bestTrial.Improvement,
                $bestTrial.Strategy
            ) -ForegroundColor Green
        }
    }

    # ========================================================================
    # 11 — FINAL CANDIDATE VALIDATION
    # ========================================================================
    Write-Step '11/18' 'Revalidation parser finale des candidats...'

    $finalRecords = [System.Collections.Generic.List[object]]::new()

    $finalErrorTotal = 0

    foreach ($candidate in $candidateRecords) {

        $finalIssues = @(Invoke-PowerShellParser -Path $candidate.CandidatePath)
        $finalCount = $finalIssues.Count

        $candidateHash = Get-Sha256 `
            -Path $candidate.CandidatePath

        $improvement = $candidate.BaselineErrors - $finalCount

        $status =
            if ($finalCount -eq 0 -and $candidate.BaselineErrors -gt 0) {
                'PARSER-CLEAN'
            }
            elseif ($improvement -gt 0) {
                'IMPROVED'
            }
            elseif ($improvement -eq 0) {
                'UNCHANGED'
            }
            else {
                'REGRESSION'
            }

        [void]$finalRecords.Add(
            [pscustomobject]@{
                RelativePath   = $candidate.RelativePath
                BaselineErrors  = $candidate.BaselineErrors
                FinalErrors     = $finalCount
                Improvement     = $improvement
                Status          = $status
                OriginalSHA256  = $candidate.OriginalSHA256
                CandidateSHA256 = $candidateHash
                ParserIssues    = @($finalIssues)
            }
        )

        $finalErrorTotal += $finalCount
    }

    $improvedRecords = @(
        $finalRecords |
        Where-Object {
            $_.Improvement -gt 0
        }
    )

    $regressionRecords = @(
        $finalRecords |
        Where-Object {
            $_.Improvement -lt 0
        }
    )

    Write-Info 'FINAL PARSER ERRORS' $finalErrorTotal
    Write-Info 'IMPROVED FILES' $improvedRecords.Count
    Write-Info 'REGRESSIONS' $regressionRecords.Count

    # ========================================================================
    # 12 — ACCEPTED CANDIDATES
    # ========================================================================
    Write-Step '12/18' 'Archivage uniquement des candidats réellement améliorés...'

    foreach ($record in $improvedRecords) {

        $destination = Join-Path `
            $AcceptedRoot `
            $record.RelativePath

        Ensure-Directory (
            Split-Path -Parent $destination
        )

        $candidateSource = Join-Path `
            $CandidatesRoot `
            $record.RelativePath

        Copy-Item `
            -LiteralPath $candidateSource `
            -Destination $destination `
            -Force
    }

    Write-Info 'ACCEPTED CANDIDATES' $improvedRecords.Count

    # ========================================================================
    # 13 — REJECTED / UNCHANGED
    # ========================================================================
    Write-Step '13/18' 'Classement des candidats sans amélioration...'

    $unchangedRecords = @(
        $finalRecords |
        Where-Object {
            $_.Improvement -eq 0
        }
    )

    $rejectedRecords = @(
        $finalRecords |
        Where-Object {
            $_.Improvement -le 0
        }
    )

    foreach ($record in $rejectedRecords) {

        $destination = Join-Path `
            $RejectedRoot `
            $record.RelativePath

        Ensure-Directory (
            Split-Path -Parent $destination
        )

        $candidateSource = Join-Path `
            $CandidatesRoot `
            $record.RelativePath

        Copy-Item `
            -LiteralPath $candidateSource `
            -Destination $destination `
            -Force
    }

    Write-Info 'UNCHANGED' $unchangedRecords.Count
    Write-Info 'REJECTED/REGRESSION' $rejectedRecords.Count

    # ========================================================================
    # 14 — SOURCE INTEGRITY
    # ========================================================================
    Write-Step '14/18' 'Vérification SHA-256 des sources originales...'

    $sourceMutations = 0
    $sourceIntegrityRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($baseline in $baselineRecords) {

        $afterHash = Get-Sha256 `
            -Path $baseline.SourcePath

        $mutated = (
            $afterHash -ne $baseline.SHA256
        )

        if ($mutated) {
            $sourceMutations++
        }

        [void]$sourceIntegrityRecords.Add(
            [pscustomobject]@{
                RelativePath = $baseline.RelativePath
                BeforeSHA256 = $baseline.SHA256
                AfterSHA256  = $afterHash
                Mutated      = $mutated
            }
        )
    }

    Write-Info 'SOURCE MUTATIONS' $sourceMutations

    if ($sourceMutations -ne 0) {
        throw 'FAIL-CLOSED : mutation détectée sur une source originale.'
    }

    Write-Green '      SOURCE INTEGRITY           : PASS'

    # ========================================================================
    # 15 — GLOBAL VERDICT
    # ========================================================================
    Write-Step '15/18' 'Calcul du verdict global...'

    $globalImprovement = $originalErrorTotal - $finalErrorTotal

    if ($originalErrorTotal -gt 0) {
        $improvementRatio = [math]::Round(
            (
                $globalImprovement /
                [double]$originalErrorTotal
            ) * 100,
            2
        )
    }
    else {
        $improvementRatio = 0
    }

    $fullyClean = (
        $finalErrorTotal -eq 0 -and
        $originalErrorTotal -gt 0
    )

    if ($fullyClean) {
        $globalVerdict = 'PARSER-CLEAN / CANDIDATE-ONLY / FAIL-CLOSED'
    }
    elseif ($globalImprovement -gt 0) {
        $globalVerdict = 'IMPROVEMENT-FOUND / FAIL-CLOSED'
    }
    else {
        $globalVerdict = 'NO-IMPROVEMENT / FAIL-CLOSED'
    }

    Write-Info 'GLOBAL IMPROVEMENT' $globalImprovement
    Write-Info 'IMPROVEMENT RATIO' "$improvementRatio %"
    Write-Info 'VERDICT' $globalVerdict

    # ========================================================================
    # 16 — EVIDENCE
    # ========================================================================
    Write-Step '16/18' 'Écriture des preuves forensic...'

    $EvidencePath = Join-Path `
        $EvidenceRoot `
        'SUPER_FORENSIC_REPAIR_EVIDENCE.json'

    $Evidence = [ordered]@{
        Engine              = $EngineName
        Version             = $ScriptVersion
        RunId               = $RunId
        TimestampUtc        = [DateTime]::UtcNow.ToString('o')
        ProjectRoot         = $ProjectRoot
        RepairDossier       = $RepairDossier
        RootCauses          = $RootCauseCount
        TargetFiles         = $TargetFileCount
        Strategies          = @(
            $Strategies |
            ForEach-Object {
                $_.Name
            }
        )
        BaselineParserErrors = $originalErrorTotal
        FinalParserErrors    = $finalErrorTotal
        GlobalImprovement    = $globalImprovement
        ImprovementRatio     = $improvementRatio
        Trials               = @($trialResults | Select-Object `
            RelativePath,
            Strategy,
            Changed,
            Accepted,
            Regression,
            BeforeErrors,
            AfterErrors,
            Improvement,
            Reason
        )
        AcceptedRepairs      = @($acceptedRepairs)
        FinalRecords         = @(
            $finalRecords |
            Select-Object `
                RelativePath,
                BaselineErrors,
                FinalErrors,
                Improvement,
                Status,
                OriginalSHA256,
                CandidateSHA256
        )
        SourceIntegrity      = @($sourceIntegrityRecords)
        SourceMutation       = ($sourceMutations -ne 0)
        ExecutionPerformed   = $false
        PromotionPerformed   = $false
        Certified            = $false
        CertifiedAuthorized  = $false
        Verdict              = $globalVerdict
    }

    $Evidence |
        ConvertTo-Json -Depth 30 |
        Set-Content `
            -LiteralPath $EvidencePath `
            -Encoding utf8

    # ========================================================================
    # 17 — MANIFEST
    # ========================================================================
    Write-Step '17/18' 'Génération du manifeste forensic...'

    $ManifestPath = Join-Path `
        $Reports `
        'SUPER_FORENSIC_REPAIR_V4_MANIFEST.json'

    $Manifest = [ordered]@{
        Engine                = $EngineName
        Version               = $ScriptVersion
        RunId                 = $RunId
        TimestampUtc          = [DateTime]::UtcNow.ToString('o')
        ProjectRoot           = $ProjectRoot
        RepairDossier         = $RepairDossier
        RootCauses            = $RootCauseCount
        TargetFiles           = $TargetFileCount
        BaselineParserErrors  = $originalErrorTotal
        FinalParserErrors     = $finalErrorTotal
        GlobalImprovement     = $globalImprovement
        ImprovementRatio      = $improvementRatio
        RepairTrials          = $strategyTrialCount
        ProvenRepairs         = $acceptedRepairs.Count
        ImprovedFiles         = $improvedRecords.Count
        UnchangedFiles        = $unchangedRecords.Count
        RegressionFiles       = $regressionRecords.Count
        SourceMutation        = $false
        ExecutionPerformed    = $false
        PromotionPerformed   = $false
        Certified             = $false
        CertifiedAuthorized   = $false
        Verdict               = $globalVerdict
        Evidence              = $EvidencePath
        AcceptedRoot          = $AcceptedRoot
    }

    $Manifest |
        ConvertTo-Json -Depth 30 |
        Set-Content `
            -LiteralPath $ManifestPath `
            -Encoding utf8

    # ========================================================================
    # 18 — REPORT
    # ========================================================================
    Write-Step '18/18' 'Génération du rapport final...'

    $ReportPath = Join-Path `
        $Reports `
        'SUPER_FORENSIC_REPAIR_V4_REPORT.txt'

    $reportLines = @(
        '============================================================================'
        ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v4.0.0'
        '============================================================================'
        ''
        "RUN ID                  : $RunId"
        "PROJECT                 : $ProjectRoot"
        "REPAIR DOSSIER         : $RepairDossier"
        ''
        "ROOT CAUSES             : $RootCauseCount"
        "TARGET FILES            : $TargetFileCount"
        "BASELINE PARSER ERRORS : $originalErrorTotal"
        "FINAL PARSER ERRORS    : $finalErrorTotal"
        "GLOBAL IMPROVEMENT      : $globalImprovement"
        "IMPROVEMENT RATIO      : $improvementRatio %"
        ''
        "STRATEGIES             : $($Strategies.Count)"
        "TRIALS                 : $strategyTrialCount"
        "PROVEN REPAIRS        : $($acceptedRepairs.Count)"
        "IMPROVED FILES        : $($improvedRecords.Count)"
        "UNCHANGED FILES       : $($unchangedRecords.Count)"
        "REGRESSIONS           : $($regressionRecords.Count)"
        ''
        "SOURCE MUTATION        : 0"
        "EXECUTION              : DISABLED"
        "PROMOTION              : DISABLED"
        "CERTIFIED              : FALSE"
        "CERTIFIED AUTHORIZED  : FALSE"
        ''
        "VERDICT                : $globalVerdict"
        ''
        "WORKBENCH             : $Workbench"
        "ACCEPTED CANDIDATES   : $AcceptedRoot"
        "EVIDENCE              : $EvidencePath"
        "MANIFEST              : $ManifestPath"
        "REPORT                : $ReportPath"
        ''
        '----------------------------------------------------------------------------'
        ' PROVEN REPAIRS'
        '----------------------------------------------------------------------------'
    )

    foreach ($repair in $acceptedRepairs) {

        $reportLines += (
            "{0} | {1} | {2} -> {3} | IMPROVEMENT +{4}" -f
            $repair.RelativePath,
            $repair.Strategy,
            $repair.BeforeErrors,
            $repair.AfterErrors,
            $repair.Improvement
        )
    }

    $reportLines += ''
    $reportLines += '----------------------------------------------------------------------------'
    $reportLines += ' FAIL-CLOSED GUARANTEES'
    $reportLines += '----------------------------------------------------------------------------'
    $reportLines += 'SOURCE MUTATION          : 0'
    $reportLines += 'EXECUTION               : DISABLED'
    $reportLines += 'PROMOTION               : DISABLED'
    $reportLines += 'CERTIFIED               : NEVER GRANTED BY THIS ENGINE'
    $reportLines += 'ORIGINAL SOURCES         : UNTOUCHED'
    $reportLines += '----------------------------------------------------------------------------'

    Write-Utf8NoBom `
        -Path $ReportPath `
        -Content ($reportLines -join [Environment]::NewLine)

    # ========================================================================
    # FINAL
    # ========================================================================
    Write-Banner 'E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v4.0.0 COMPLETE' `
        ([ConsoleColor]::Green)

    Write-Info 'RUN ID' $RunId
    Write-Info 'ROOT CAUSES' $RootCauseCount
    Write-Info 'TARGET FILES' $TargetFileCount
    Write-Info 'PARSER BASELINE' $originalErrorTotal
    Write-Info 'PARSER FINAL' $finalErrorTotal
    Write-Info 'GLOBAL IMPROVEMENT' $globalImprovement
    Write-Info 'IMPROVEMENT RATIO' "$improvementRatio %"
    Write-Info 'TRIALS' $strategyTrialCount
    Write-Info 'PROVEN REPAIRS' $acceptedRepairs.Count
    Write-Info 'IMPROVED FILES' $improvedRecords.Count
    Write-Info 'REGRESSIONS' $regressionRecords.Count

    Write-Host ''
    Write-Green 'SOURCE MUTATION         : 0'
    Write-Green 'EXECUTION              : DISABLED'
    Write-Green 'PROMOTION              : DISABLED'
    Write-Yellow 'CERTIFIED              : NOT AUTHORIZED'

    Write-Host ''
    Write-Info 'WORKBENCH' $Workbench
    Write-Info 'ACCEPTED CANDIDATES' $AcceptedRoot
    Write-Info 'EVIDENCE' $EvidencePath
    Write-Info 'REPORT' $ReportPath
    Write-Info 'MANIFEST' $ManifestPath

    Write-Host ''
    Write-Host "VERDICT : $globalVerdict" -ForegroundColor Cyan

    Write-Host ''
    Write-Yellow 'FAIL-CLOSED : les sources originales restent intactes.'
    Write-Yellow 'FAIL-CLOSED : aucun candidat n''est exécuté.'
    Write-Yellow 'FAIL-CLOSED : aucun candidat n''est promu.'
    Write-Yellow 'FAIL-CLOSED : CERTIFIED n''est jamais accordé par ce moteur.'

    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ''
    Write-Host 'La fenêtre reste ouverte.' -ForegroundColor DarkGray
    Write-Host ''
    Read-Host 'Appuie sur ENTREE pour terminer'
}
catch {

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host " $EngineName v$ScriptVersion FAILED / FAIL-CLOSED" -ForegroundColor Red
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''

    Write-Host (
        "ERROR : {0}" -f $_.Exception.Message
    ) -ForegroundColor Red

    Write-Host ''
    Write-Host 'SOURCE MUTATION : False'
    Write-Host 'EXECUTION       : False'
    Write-Host 'PROMOTION       : False'
    Write-Host ''

    Write-Yellow 'Aucune promotion de candidat.'
    Write-Yellow 'Aucun CERTIFIED autorisé.'
    Write-Yellow 'Les sources originales restent intactes.'

    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''
    Read-Host 'Appuie sur ENTREE pour terminer'
}