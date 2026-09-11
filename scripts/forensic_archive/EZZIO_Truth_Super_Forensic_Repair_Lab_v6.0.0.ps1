# ============================================================================
# E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v6.0.0
# ============================================================================
# MODE        : READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED
# QUALITY     : FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE
#
# OBJECTIF
#   - Charger le dernier REPAIR_DOSSIER
#   - Identifier les fichiers PowerShell réellement concernés
#   - Construire un baseline SHA-256 + parser
#   - Cloner les sources dans une zone candidate
#   - Générer des hypothèses mécaniques déterministes
#   - Tester chaque hypothèse dans une copie isolée
#   - Mesurer AVANT / APRÈS
#   - Rejeter toute régression
#   - Ne jamais modifier les sources originales
#   - Ne jamais exécuter les candidats
#   - Ne jamais promouvoir automatiquement
#
# IMPORTANT
#   Ce moteur NE déclare jamais CERTIFIED.
#   Il produit uniquement des preuves et des candidats.
# ============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION
# ============================================================================

$EngineName   = 'E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB'
$ScriptVersion = '6.0.0'

$ProjectRoot = 'G:\AI\E-zzio'

$ReportsRoot = Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'

$SourceMutation      = $false
$ExecutionPerformed  = $false
$PromotionPerformed  = $false

$InvariantFailure = $false
$FatalMessage = $null

# ============================================================================
# UTILITAIRES
# ============================================================================

function Write-Banner {
    param(
        [string]$Title
    )

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Cyan
    Write-Host (" {0}" -f $Title) -ForegroundColor Cyan
    Write-Host '============================================================================' -ForegroundColor Cyan
}

function Write-Step {
    param(
        [string]$Step,
        [string]$Text
    )

    Write-Host ''
    Write-Host ("[{0}] {1}" -f $Step, $Text) -ForegroundColor White
}

function Write-Info {
    param(
        [string]$Name,
        [object]$Value
    )

    Write-Host ("      {0,-27}: {1}" -f $Name, $Value)
}

function Write-Ok {
    param(
        [string]$Text
    )

    Write-Host ("      {0}" -f $Text) -ForegroundColor Green
}

function Write-Warn {
    param(
        [string]$Text
    )

    Write-Host ("      {0}" -f $Text) -ForegroundColor Yellow
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [AllowEmptyString()]
        [string]$Content
    )

    $utf8 = New-Object System.Text.UTF8Encoding($false)

    [System.IO.File]::WriteAllText(
        $Path,
        $(if ($null -eq $Content) { '' } else { $Content }),
        $utf8
    )
}

function Get-Sha256 {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Get-RelativePathSafe {
    param(
        [Parameter(Mandatory)]
        [string]$BasePath,

        [Parameter(Mandatory)]
        [string]$FullPath
    )

    $baseFull = [System.IO.Path]::GetFullPath($BasePath)
    $fileFull = [System.IO.Path]::GetFullPath($FullPath)

    if (-not $baseFull.EndsWith('\')) {
        $baseFull = $baseFull + '\'
    }

    $baseUri = [System.Uri]::new($baseFull)
    $fileUri = [System.Uri]::new($fileFull)

    $relativeUri = $baseUri.MakeRelativeUri($fileUri)

    return [System.Uri]::UnescapeDataString(
        $relativeUri.ToString()
    ).Replace('/', '\')
}

function Normalize-Text {
    param(
        [AllowEmptyString()]
        [string]$Text
    )

    if ($null -eq $Text) {
        return ''
    }

    # IMPORTANT :
    # Chaque transformation est stockée séparément.
    # Aucun chaînage .Replace() multi-ligne fragile.

    $result = $Text

    $result = $result.Replace([string][char]0x2018, "'")
    $result = $result.Replace([string][char]0x2019, "'")
    $result = $result.Replace([string][char]0x201C, '"')
    $result = $result.Replace([string][char]0x201D, '"')

    $result = $result.Replace([string][char]0x2013, '-')
    $result = $result.Replace([string][char]0x2014, '-')
    $result = $result.Replace([string][char]0x2212, '-')

    $result = $result.Replace([string][char]0xFEFF, '')
    $result = $result.Replace([string][char]0x200B, '')
    $result = $result.Replace([string][char]0x200C, '')
    $result = $result.Replace([string][char]0x200D, '')
    $result = $result.Replace([string][char]0x2060, '')

    return $result
}

function Normalize-LineEndings {
    param(
        [AllowEmptyString()]
        [string]$Text
    )

    if ($null -eq $Text) {
        return ''
    }

    $result = $Text

    $result = $result.Replace("`r`n", "`n")
    $result = $result.Replace("`r", "`n")

    return $result
}

function Test-PathInsideRoot {
    param(
        [Parameter(Mandatory)]
        [string]$Root,

        [Parameter(Mandatory)]
        [string]$Candidate
    )

    $rootFull = [System.IO.Path]::GetFullPath($Root)
    $candidateFull = [System.IO.Path]::GetFullPath($Candidate)

    if (-not $rootFull.EndsWith('\')) {
        $rootFull = $rootFull + '\'
    }

    return $candidateFull.StartsWith(
        $rootFull,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Get-PowerShellParseResult {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $tokens = $null
    $parseErrors = $null

    try {
        $null = [System.Management.Automation.Language.Parser]::ParseFile(
            $Path,
            [ref]$tokens,
            [ref]$parseErrors
        )
    }
    catch {
        $message = $_.Exception.Message

        return [pscustomobject]@{
            Path       = $Path
            ErrorCount = 1
            Errors     = @(
                [pscustomobject]@{
                    Message = $message
                    Line    = 0
                    Column  = 0
                    Text    = ''
                }
            )
        }
    }

    $records = @()

    foreach ($parseItem in @($parseErrors)) {
        if ($null -eq $parseItem) {
            continue
        }

        $line = 0
        $column = 0
        $text = ''

        if ($null -ne $parseItem.Extent) {
            $line = $parseItem.Extent.StartLineNumber
            $column = $parseItem.Extent.StartColumnNumber
            $text = $parseItem.Extent.Text
        }

        $records += [pscustomobject]@{
            Message = [string]$parseItem.Message
            Line    = $line
            Column  = $column
            Text    = $text
        }
    }

    return [pscustomobject]@{
        Path       = $Path
        ErrorCount = $records.Count
        Errors     = $records
    }
}

function Get-TextLines {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $content = [System.IO.File]::ReadAllText($Path)

    if ([string]::IsNullOrEmpty($content)) {
        return @()
    }

    return @(
        $content -split "`r`n|`n|`r", -1
    )
}

function Set-TextFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [AllowEmptyString()]
        [string]$Content
    )

    Write-Utf8NoBom -Path $Path -Content $Content
}

function Apply-Strategy {
    param(
        [Parameter(Mandatory)]
        [string]$Strategy,

        [Parameter(Mandatory)]
        [string]$Content
    )

    $original = if ($null -eq $Content) { '' } else { $Content }
    $candidate = $original

    switch ($Strategy) {

        'SMART_QUOTES' {
            $candidate = Normalize-Text -Text $candidate
        }

        'UNICODE_DASHES' {
            $candidate = $candidate.Replace([string][char]0x2013, '-')
            $candidate = $candidate.Replace([string][char]0x2014, '-')
            $candidate = $candidate.Replace([string][char]0x2212, '-')
        }

        'INVISIBLE_CHARS' {
            $candidate = $candidate.Replace([string][char]0xFEFF, '')
            $candidate = $candidate.Replace([string][char]0x200B, '')
            $candidate = $candidate.Replace([string][char]0x200C, '')
            $candidate = $candidate.Replace([string][char]0x200D, '')
            $candidate = $candidate.Replace([string][char]0x2060, '')
        }

        'MARKDOWN_FENCES' {
            $candidate = $candidate.Replace('```powershell', '')
            $candidate = $candidate.Replace('```PowerShell', '')
            $candidate = $candidate.Replace('```pwsh', '')
            $candidate = $candidate.Replace('```', '')
        }

        'CONSOLE_PROMPTS' {
            $lines = @(
                $candidate -split "`r`n|`n|`r", -1
            )

            $kept = New-Object System.Collections.Generic.List[string]

            foreach ($line in $lines) {
                if ($line -match '^\s*PS\s+[^>]+>\s?') {
                    continue
                }

                $null = $kept.Add($line)
            }

            $candidate = $kept -join "`n"
        }

        'BACKTICK_WHITESPACE' {
            $candidate = $candidate.Replace("`r`n", "`n")
            $candidate = $candidate.Replace("`r", "`n")
        }

        'NUL_CHARS' {
            $candidate = $candidate.Replace([string][char]0, '')
        }

        'LINE_ENDINGS' {
            $candidate = Normalize-LineEndings -Text $candidate
        }

        'TRANSCRIPT_MARKERS' {
            $lines = @(
                $candidate -split "`r`n|`n|`r", -1
            )

            $kept = New-Object System.Collections.Generic.List[string]

            foreach ($line in $lines) {

                if ($line -match '^\s*>>\s?') {
                    continue
                }

                if ($line -match '^\s*PS\s+[^>]+>\s?') {
                    continue
                }

                $null = $kept.Add($line)
            }

            $candidate = $kept -join "`n"
        }

        default {
            throw "Unknown repair strategy: $Strategy"
        }
    }

    return $candidate
}

# ============================================================================
# MAIN
# ============================================================================

try {

    Write-Banner "$EngineName v$ScriptVersion"

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
        throw "Project root introuvable: $ProjectRoot"
    }

    if (-not (Test-Path -LiteralPath $ReportsRoot -PathType Container)) {
        New-Item -ItemType Directory -Path $ReportsRoot -Force | Out-Null
    }

    $PowerShellVersion = $PSVersionTable.PSVersion.ToString()

    Write-Info 'POWERSHELL' $PowerShellVersion
    Write-Ok 'ENVIRONMENT : PASS'

    # ========================================================================
    # SELF PARSER CHECK
    # ========================================================================

    Write-Step '2/18' 'Auto-validation syntaxique du moteur...'

    $SelfPath = $MyInvocation.MyCommand.Path

    if ([string]::IsNullOrWhiteSpace($SelfPath)) {
        throw 'Impossible de déterminer le chemin du moteur courant.'
    }

    $selfParse = Get-PowerShellParseResult -Path $SelfPath

    Write-Info 'SELF PARSER ERRORS' $selfParse.ErrorCount

    if ($selfParse.ErrorCount -ne 0) {
        throw "Le moteur v$ScriptVersion contient lui-même $($selfParse.ErrorCount) erreur(s) parser."
    }

    Write-Ok 'SELF PARSER : PASS'

    # ========================================================================
    # 3 — DISCOVERY
    # ========================================================================

    Write-Step '3/18' 'Recherche du dernier REPAIR_DOSSIER...'

    $repairDossiers = @(
        Get-ChildItem `
            -LiteralPath $ReportsRoot `
            -Directory `
            -ErrorAction Stop |
        Where-Object {
            Test-Path `
                -LiteralPath (Join-Path $_.FullName 'REPAIR_DOSSIER') `
                -PathType Container
        } |
        Sort-Object LastWriteTimeUtc -Descending
    )

    if ($repairDossiers.Count -eq 0) {
        throw 'Aucun REPAIR_DOSSIER trouvé.'
    }

    $RepairDossier = Join-Path `
        $repairDossiers[0].FullName `
        'REPAIR_DOSSIER'

    $MatrixPath = Join-Path `
        $RepairDossier `
        'ROOT_CAUSE_MATRIX.json'

    if (-not (Test-Path -LiteralPath $MatrixPath -PathType Leaf)) {
        throw "ROOT_CAUSE_MATRIX.json introuvable: $MatrixPath"
    }

    Write-Info 'DOSSIER' $RepairDossier
    Write-Info 'MATRIX' $MatrixPath
    Write-Ok 'DISCOVERY : PASS'

    # ========================================================================
    # 4 — ROOT MATRIX
    # ========================================================================

    Write-Step '4/18' 'Chargement de la Root-Cause Matrix...'

    $RootMatrix = Get-Content `
        -LiteralPath $MatrixPath `
        -Raw `
        -ErrorAction Stop |
        ConvertFrom-Json

    $RootCauses = @($RootMatrix)

    $RootCauseCount = $RootCauses.Count

    Write-Info 'ROOT CAUSES' $RootCauseCount

    if ($RootCauseCount -eq 0) {
        throw 'Root-Cause Matrix vide.'
    }

    # ========================================================================
    # 5 — TARGET FILE DISCOVERY
    # ========================================================================

    Write-Step '5/18' 'Identification forensic des fichiers cibles...'

    $candidatePathSet = New-Object `
        System.Collections.Generic.HashSet[string](
            [System.StringComparer]::OrdinalIgnoreCase
        )

    foreach ($root in $RootCauses) {

        if ($null -eq $root) {
            continue
        }

        $properties = $root.PSObject.Properties

        foreach ($property in $properties) {

            $value = $property.Value

            if ($value -is [string]) {

                if ($value -match '(?i)\.ps1$') {

                    $rawPath = $value

                    if (-not [System.IO.Path]::IsPathRooted($rawPath)) {
                        $rawPath = Join-Path $ProjectRoot $rawPath
                    }

                    try {
                        $fullPath = [System.IO.Path]::GetFullPath($rawPath)
                    }
                    catch {
                        continue
                    }

                    if (
                        (Test-Path -LiteralPath $fullPath -PathType Leaf) -and
                        (Test-PathInsideRoot -Root $ProjectRoot -Candidate $fullPath)
                    ) {
                        $null = $candidatePathSet.Add($fullPath)
                    }
                }
            }
        }
    }

    # Fallback contrôlé :
    # si la matrice ne permet pas de reconstruire les chemins, utiliser
    # uniquement les PowerShell mentionnés dans le dossier forensic.

    if ($candidatePathSet.Count -eq 0) {

        $fallbackFiles = @(
            Get-ChildItem `
                -LiteralPath $RepairDossier `
                -File `
                -Recurse `
                -Filter '*.json' `
                -ErrorAction SilentlyContinue
        )

        foreach ($jsonFile in $fallbackFiles) {

            try {
                $jsonText = Get-Content `
                    -LiteralPath $jsonFile.FullName `
                    -Raw `
                    -ErrorAction Stop

                $matches = [regex]::Matches(
                    $jsonText,
                    '(?i)(?:[A-Z]:\\[^"`r`n]+|[^"`r`n]+)\.ps1'
                )

                foreach ($match in $matches) {

                    $raw = $match.Value.Trim(
                        '"',
                        "'",
                        ' ',
                        "`t"
                    )

                    if (-not [System.IO.Path]::IsPathRooted($raw)) {
                        $raw = Join-Path $ProjectRoot $raw
                    }

                    try {
                        $full = [System.IO.Path]::GetFullPath($raw)
                    }
                    catch {
                        continue
                    }

                    if (
                        (Test-Path -LiteralPath $full -PathType Leaf) -and
                        (Test-PathInsideRoot -Root $ProjectRoot -Candidate $full)
                    ) {
                        $null = $candidatePathSet.Add($full)
                    }
                }
            }
            catch {
                continue
            }
        }
    }

    $TargetFiles = @(
        $candidatePathSet |
        Sort-Object
    )

    $TargetFileCount = $TargetFiles.Count

    Write-Info 'TARGET FILES' $TargetFileCount

    if ($TargetFileCount -eq 0) {
        throw 'Aucun fichier PowerShell cible identifié.'
    }

    # ========================================================================
    # 6 — LAB
    # ========================================================================

    Write-Step '6/18' 'Création du laboratoire forensic...'

    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    $nonce = [guid]::NewGuid().ToString('N').Substring(0, 12)

    $RunId = "{0}_{1}" -f $timestamp, $nonce

    $RunRoot = Join-Path `
        $ReportsRoot `
        $RunId

    $Workbench = Join-Path `
        $RunRoot `
        'SUPER_FORENSIC_REPAIR_LAB'

    $OriginalsRoot = Join-Path `
        $Workbench `
        'ORIGINAL_METADATA'

    $CandidatesRoot = Join-Path `
        $Workbench `
        'CANDIDATES'

    $EvidenceRoot = Join-Path `
        $Workbench `
        'EVIDENCE'

    $ReportsDir = Join-Path `
        $Workbench `
        'REPORTS'

    $AcceptedRoot = Join-Path `
        $Workbench `
        'ACCEPTED_CANDIDATES'

    foreach ($dir in @(
        $Workbench,
        $OriginalsRoot,
        $CandidatesRoot,
        $EvidenceRoot,
        $ReportsDir,
        $AcceptedRoot
    )) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    Write-Info 'RUN ID' $RunId
    Write-Info 'WORKBENCH' $Workbench
    Write-Ok 'WORKBENCH : PASS'

    # ========================================================================
    # 7 — BASELINE
    # ========================================================================

    Write-Step '7/18' 'Construction du baseline SHA-256 + parser original...'

    $BaselineRecords = New-Object System.Collections.Generic.List[object]

    foreach ($sourcePath in $TargetFiles) {

        $relative = Get-RelativePathSafe `
            -BasePath $ProjectRoot `
            -FullPath $sourcePath

        $sha = Get-Sha256 -Path $sourcePath

        $parse = Get-PowerShellParseResult -Path $sourcePath

        $BaselineRecords.Add(
            [pscustomobject]@{
                SourcePath = $sourcePath
                RelativePath = $relative
                SHA256 = $sha
                ParserErrors = $parse.ErrorCount
                Errors = @($parse.Errors)
            }
        )
    }

    $OriginalErrorCount = (
        $BaselineRecords |
        Measure-Object -Property ParserErrors -Sum
    ).Sum

    if ($null -eq $OriginalErrorCount) {
        $OriginalErrorCount = 0
    }

    Write-Info 'BASELINE FILES' $BaselineRecords.Count
    Write-Info 'PARSER ERRORS' $OriginalErrorCount

    $baselineJson = $BaselineRecords | ConvertTo-Json -Depth 20

    Write-Utf8NoBom `
        -Path (Join-Path $EvidenceRoot 'BASELINE.json') `
        -Content $baselineJson

    # ========================================================================
    # 8 — CLONING
    # ========================================================================

    Write-Step '8/18' 'Clonage strict des sources...'

    $CandidateRecords = New-Object System.Collections.Generic.List[object]

    foreach ($record in $BaselineRecords) {

        $relative = $record.RelativePath

        $destination = Join-Path `
            $CandidatesRoot `
            $relative

        $destinationParent = Split-Path `
            -Parent `
            $destination

        if (-not (Test-Path -LiteralPath $destinationParent -PathType Container)) {
            New-Item `
                -ItemType Directory `
                -Path $destinationParent `
                -Force |
                Out-Null
        }

        Copy-Item `
            -LiteralPath $record.SourcePath `
            -Destination $destination `
            -Force `
            -ErrorAction Stop

        $cloneHash = Get-Sha256 -Path $destination

        if ($cloneHash -ne $record.SHA256) {
            throw "Hash mismatch pendant le clonage: $relative"
        }

        $CandidateRecords.Add(
            [pscustomobject]@{
                SourcePath = $record.SourcePath
                CandidatePath = $destination
                RelativePath = $relative
                OriginalSHA256 = $record.SHA256
                CandidateSHA256 = $cloneHash
            }
        )
    }

    Write-Info 'CLONED' $CandidateRecords.Count

    if ($CandidateRecords.Count -ne $BaselineRecords.Count) {
        throw 'Le nombre de clones ne correspond pas au baseline.'
    }

    # ========================================================================
    # 9 — CANDIDATE BASELINE
    # ========================================================================

    Write-Step '9/18' 'Revalidation parser des candidats clonés...'

    $CandidateBaseline = New-Object System.Collections.Generic.List[object]

    foreach ($candidate in $CandidateRecords) {

        $parse = Get-PowerShellParseResult `
            -Path $candidate.CandidatePath

        $CandidateBaseline.Add(
            [pscustomobject]@{
                RelativePath = $candidate.RelativePath
                CandidatePath = $candidate.CandidatePath
                ParserErrors = $parse.ErrorCount
                Errors = @($parse.Errors)
            }
        )
    }

    $CandidateBaselineErrors = (
        $CandidateBaseline |
        Measure-Object -Property ParserErrors -Sum
    ).Sum

    if ($null -eq $CandidateBaselineErrors) {
        $CandidateBaselineErrors = 0
    }

    Write-Info 'CANDIDATE BASELINE' $CandidateBaselineErrors

    # ========================================================================
    # 10 — ERROR QUEUE
    # ========================================================================

    Write-Step '10/18' 'Construction de la file des erreurs parser...'

    $ErrorQueue = New-Object System.Collections.Generic.List[object]

    foreach ($candidate in $CandidateBaseline) {

        foreach ($parseRecord in @($candidate.Errors)) {

            if ($null -eq $parseRecord) {
                continue
            }

            $ErrorQueue.Add(
                [pscustomobject]@{
                    RelativePath = $candidate.RelativePath
                    CandidatePath = $candidate.CandidatePath
                    Line = $parseRecord.Line
                    Column = $parseRecord.Column
                    Message = [string]$parseRecord.Message
                    Text = [string]$parseRecord.Text
                }
            )
        }
    }

    Write-Info 'ERROR QUEUE' $ErrorQueue.Count

    # ========================================================================
    # 11 — STRATEGIES
    # ========================================================================

    Write-Step '11/18' 'Chargement des stratégies de réparation...'

    $Strategies = @(
        'SMART_QUOTES'
        'UNICODE_DASHES'
        'INVISIBLE_CHARS'
        'MARKDOWN_FENCES'
        'CONSOLE_PROMPTS'
        'BACKTICK_WHITESPACE'
        'NUL_CHARS'
        'LINE_ENDINGS'
        'TRANSCRIPT_MARKERS'
    )

    Write-Info 'STRATEGIES' $Strategies.Count

    foreach ($strategy in $Strategies) {
        Write-Host ("      - {0}" -f $strategy)
    }

    # ========================================================================
    # 12 — STRATEGY SCAN
    # ========================================================================

    Write-Step '12/18' 'Scan déterministe de toutes les stratégies...'

    $AttemptRecords = New-Object System.Collections.Generic.List[object]

    foreach ($candidateRecord in $CandidateRecords) {

        $originalContent = [System.IO.File]::ReadAllText(
            $candidateRecord.CandidatePath
        )

        $candidateBaseline = $CandidateBaseline |
            Where-Object {
                $_.RelativePath -eq $candidateRecord.RelativePath
            } |
            Select-Object -First 1

        if ($null -eq $candidateBaseline) {
            continue
        }

        foreach ($strategy in $Strategies) {

            # Chaque tentative travaille sur une COPIE ISOLÉE.
            $trialRoot = Join-Path `
                $EvidenceRoot `
                'TRIALS'

            $trialRelative = $candidateRecord.RelativePath

            $trialPath = Join-Path `
                $trialRoot `
                $strategy

            $trialPath = Join-Path `
                $trialPath `
                $trialRelative

            $trialParent = Split-Path `
                -Parent `
                $trialPath

            New-Item `
                -ItemType Directory `
                -Path $trialParent `
                -Force |
                Out-Null

            Set-TextFile `
                -Path $trialPath `
                -Content $originalContent

            $trialContent = Apply-Strategy `
                -Strategy $strategy `
                -Content $originalContent

            $changed = $trialContent -cne $originalContent

            if ($changed) {
                Set-TextFile `
                    -Path $trialPath `
                    -Content $trialContent
            }

            $trialParse = Get-PowerShellParseResult `
                -Path $trialPath

            $before = [int]$candidateBaseline.ParserErrors
            $after = [int]$trialParse.ErrorCount
            $delta = $before - $after

            $classification = 'NO_CHANGE'

            if ($after -lt $before) {
                $classification = 'IMPROVED'
            }
            elseif ($after -gt $before) {
                $classification = 'REGRESSION'
            }
            elseif ($changed) {
                $classification = 'CHANGED_NO_IMPROVEMENT'
            }

            $trialHash = Get-Sha256 -Path $trialPath

            $AttemptRecords.Add(
                [pscustomobject]@{
                    RelativePath = $candidateRecord.RelativePath
                    Strategy = $strategy
                    TrialPath = $trialPath
                    BeforeErrors = $before
                    AfterErrors = $after
                    Improvement = $delta
                    Changed = $changed
                    Classification = $classification
                    TrialSHA256 = $trialHash
                }
            )
        }
    }

    Write-Info 'ATTEMPTS' $AttemptRecords.Count

    # ========================================================================
    # 13 — SELECTION
    # ========================================================================

    Write-Step '13/18' 'Sélection stricte des candidats réellement améliorés...'

    $ImprovedRecords = @(
        $AttemptRecords |
        Where-Object {
            $_.Classification -eq 'IMPROVED' -and
            $_.Improvement -gt 0
        } |
        Sort-Object `
            RelativePath,
            @{ Expression = 'Improvement'; Descending = $true }
    )

    $RegressionRecords = @(
        $AttemptRecords |
        Where-Object {
            $_.Classification -eq 'REGRESSION'
        }
    )

    $RejectedRecords = @(
        $AttemptRecords |
        Where-Object {
            $_.Classification -ne 'IMPROVED'
        }
    )

    # Une seule meilleure stratégie par fichier.
    $AcceptedRecords = New-Object System.Collections.Generic.List[object]

    foreach ($group in (
        $ImprovedRecords |
        Group-Object RelativePath
    )) {

        $best = $group.Group |
            Sort-Object `
                @{ Expression = 'AfterErrors'; Ascending = $true },
                @{ Expression = 'Improvement'; Descending = $true },
                Strategy |
            Select-Object -First 1

        if ($null -ne $best) {
            $AcceptedRecords.Add($best)
        }
    }

    Write-Info 'IMPROVED' $ImprovedRecords.Count
    Write-Info 'ACCEPTED' $AcceptedRecords.Count
    Write-Info 'REJECTED' $RejectedRecords.Count
    Write-Info 'REGRESSIONS' $RegressionRecords.Count

    # ========================================================================
    # 14 — ARCHIVE ACCEPTED CANDIDATES
    # ========================================================================

    Write-Step '14/18' 'Archivage des candidats améliorés...'

    foreach ($accepted in $AcceptedRecords) {

        $destination = Join-Path `
            $AcceptedRoot `
            $accepted.RelativePath

        $parent = Split-Path `
            -Parent `
            $destination

        New-Item `
            -ItemType Directory `
            -Path $parent `
            -Force |
            Out-Null

        Copy-Item `
            -LiteralPath $accepted.TrialPath `
            -Destination $destination `
            -Force

        # Validation hash de l'artefact archivé.
        $acceptedHash = Get-Sha256 -Path $destination

        if ($acceptedHash -ne $accepted.TrialSHA256) {
            throw "Hash mismatch candidat accepté: $($accepted.RelativePath)"
        }
    }

    # ========================================================================
    # 15 — GLOBAL METRICS
    # ========================================================================

    Write-Step '15/18' 'Calcul des métriques globales...'

    $FinalParserErrors = $OriginalErrorCount
    $GlobalImprovement = 0

    foreach ($accepted in $AcceptedRecords) {
        $GlobalImprovement += [int]$accepted.Improvement
    }

    if ($OriginalErrorCount -gt 0) {
        $ImprovementRatio = [math]::Round(
            (
                [double]$GlobalImprovement /
                [double]$OriginalErrorCount
            ) * 100,
            2
        )
    }
    else {
        $ImprovementRatio = 0
    }

    if ($AcceptedRecords.Count -gt 0) {

        $FinalParserErrors = (
            $AcceptedRecords |
            Measure-Object -Property AfterErrors -Sum
        ).Sum

        if ($null -eq $FinalParserErrors) {
            $FinalParserErrors = $OriginalErrorCount
        }
    }

    $GlobalVerdict = 'NO-IMPROVEMENT / FAIL-CLOSED'

    if (
        $GlobalImprovement -gt 0 -and
        $RegressionRecords.Count -eq 0
    ) {
        $GlobalVerdict = 'IMPROVEMENT-FOUND / PROMOTION-DISABLED'
    }

    Write-Info 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-Info 'IMPROVEMENT RATIO' "$ImprovementRatio %"
    Write-Info 'VERDICT' $GlobalVerdict

    # ========================================================================
    # 16 — SOURCE INTEGRITY
    # ========================================================================

    Write-Step '16/18' 'Vérification de l''intégrité des sources originales...'

    $SourceMutationsDetected = 0

    foreach ($baseline in $BaselineRecords) {

        $currentHash = Get-Sha256 `
            -Path $baseline.SourcePath

        if ($currentHash -ne $baseline.SHA256) {
            $SourceMutationsDetected++
        }
    }

    Write-Info 'SOURCE MUTATIONS' $SourceMutationsDetected

    if ($SourceMutationsDetected -ne 0) {

        $SourceMutation = $true
        $InvariantFailure = $true

        throw "VIOLATION CRITIQUE : $SourceMutationsDetected source(s) modifiée(s)."
    }

    Write-Ok 'SOURCE INTEGRITY : PASS'

    # ========================================================================
    # 17 — EVIDENCE
    # ========================================================================

    Write-Step '17/18' 'Génération des preuves forensic...'

    $EvidenceObject = [ordered]@{
        Engine = $EngineName
        Version = $ScriptVersion
        RunId = $RunId
        TimestampUtc = [DateTime]::UtcNow.ToString('o')
        ProjectRoot = $ProjectRoot
        RepairDossier = $RepairDossier
        RootCauses = $RootCauseCount
        TargetFiles = $TargetFileCount
        BaselineParserErrors = $OriginalErrorCount
        CandidateBaselineErrors = $CandidateBaselineErrors
        Attempts = $AttemptRecords.Count
        Improved = $ImprovedRecords.Count
        Accepted = $AcceptedRecords.Count
        Rejected = $RejectedRecords.Count
        Regressions = $RegressionRecords.Count
        GlobalImprovement = $GlobalImprovement
        ImprovementRatio = $ImprovementRatio
        SourceMutations = $SourceMutationsDetected
        ExecutionPerformed = $ExecutionPerformed
        PromotionPerformed = $PromotionPerformed
        Certified = $false
        CertifiedAuthorized = $false
        Verdict = $GlobalVerdict
        AttemptsEvidence = @($AttemptRecords)
    }

    $EvidencePath = Join-Path `
        $EvidenceRoot `
        'SUPER_FORENSIC_REPAIR_EVIDENCE.json'

    $EvidenceJson = $EvidenceObject |
        ConvertTo-Json -Depth 30

    Write-Utf8NoBom `
        -Path $EvidencePath `
        -Content $EvidenceJson

    # ========================================================================
    # 18 — MANIFEST + REPORT
    # ========================================================================

    Write-Step '18/18' 'Génération du manifeste et du rapport final...'

    $Manifest = [ordered]@{
        Engine = $EngineName
        Version = $ScriptVersion
        RunId = $RunId
        TimestampUtc = [DateTime]::UtcNow.ToString('o')
        ProjectRoot = $ProjectRoot
        RepairDossier = $RepairDossier
        RootCauses = $RootCauseCount
        TargetFiles = $TargetFileCount
        BaselineParserErrors = $OriginalErrorCount
        CandidateBaselineErrors = $CandidateBaselineErrors
        FinalCandidateErrors = $FinalParserErrors
        GlobalImprovement = $GlobalImprovement
        ImprovementRatio = $ImprovementRatio
        RepairAttempts = $AttemptRecords.Count
        ImprovedCandidates = $ImprovedRecords.Count
        AcceptedCandidates = $AcceptedRecords.Count
        RejectedCandidates = $RejectedRecords.Count
        RegressionCandidates = $RegressionRecords.Count
        SourceMutation = $SourceMutation
        SourceMutationsDetected = $SourceMutationsDetected
        ExecutionPerformed = $ExecutionPerformed
        PromotionPerformed = $PromotionPerformed
        Certified = $false
        CertifiedAuthorized = $false
        Verdict = $GlobalVerdict
    }

    $ManifestPath = Join-Path `
        $ReportsDir `
        'SUPER_FORENSIC_REPAIR_V6_MANIFEST.json'

    $ManifestJson = $Manifest |
        ConvertTo-Json -Depth 30

    Write-Utf8NoBom `
        -Path $ManifestPath `
        -Content $ManifestJson

    $ReportPath = Join-Path `
        $ReportsDir `
        'SUPER_FORENSIC_REPAIR_V6_REPORT.txt'

    $reportLines = @(
        '============================================================================'
        ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v6.0.0'
        '============================================================================'
        ''
        "RUN ID                  : $RunId"
        "PROJECT                 : $ProjectRoot"
        "REPAIR DOSSIER         : $RepairDossier"
        ''
        "ROOT CAUSES             : $RootCauseCount"
        "TARGET FILES            : $TargetFileCount"
        "BASELINE PARSER ERRORS : $OriginalErrorCount"
        "CANDIDATE BASELINE     : $CandidateBaselineErrors"
        "FINAL CANDIDATE ERRORS : $FinalParserErrors"
        "GLOBAL IMPROVEMENT     : $GlobalImprovement"
        "IMPROVEMENT RATIO      : $ImprovementRatio %"
        ''
        "ATTEMPTS                : $($AttemptRecords.Count)"
        "IMPROVED                : $($ImprovedRecords.Count)"
        "ACCEPTED                : $($AcceptedRecords.Count)"
        "REJECTED                : $($RejectedRecords.Count)"
        "REGRESSIONS             : $($RegressionRecords.Count)"
        ''
        "SOURCE MUTATION         : $SourceMutation"
        "EXECUTION               : $ExecutionPerformed"
        "PROMOTION               : $PromotionPerformed"
        "CERTIFIED               : FALSE"
        "CERTIFIED AUTHORIZED   : FALSE"
        ''
        "VERDICT                 : $GlobalVerdict"
        ''
        "WORKBENCH               : $Workbench"
        "ACCEPTED CANDIDATES     : $AcceptedRoot"
        "EVIDENCE                : $EvidencePath"
        "MANIFEST                : $ManifestPath"
        "REPORT                  : $ReportPath"
        ''
        'FAIL-CLOSED : aucune source originale n''a été modifiée.'
        'FAIL-CLOSED : aucun code candidat n''a été exécuté.'
        'FAIL-CLOSED : aucune promotion automatique n''a été effectuée.'
        'FAIL-CLOSED : CERTIFIED n''est jamais accordé par ce moteur.'
        '============================================================================'
    )

    Write-Utf8NoBom `
        -Path $ReportPath `
        -Content ($reportLines -join [Environment]::NewLine)

    # ========================================================================
    # FINAL HARD GATES
    # ========================================================================

    if ($SourceMutationsDetected -ne 0) {
        throw 'FINAL GATE FAILURE : source mutation détectée.'
    }

    if ($ExecutionPerformed) {
        throw 'FINAL GATE FAILURE : execution interdite détectée.'
    }

    if ($PromotionPerformed) {
        throw 'FINAL GATE FAILURE : promotion interdite détectée.'
    }

    # ========================================================================
    # FINAL
    # ========================================================================

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v6.0.0 COMPLETE' -ForegroundColor Green
    Write-Host '============================================================================' -ForegroundColor Green

    Write-Info 'RUN ID' $RunId
    Write-Info 'ROOT CAUSES' $RootCauseCount
    Write-Info 'TARGET FILES' $TargetFileCount
    Write-Info 'PARSER BASELINE' $OriginalErrorCount
    Write-Info 'PARSER FINAL' $FinalParserErrors
    Write-Info 'GLOBAL IMPROVEMENT' $GlobalImprovement
    Write-Info 'ATTEMPTS' $AttemptRecords.Count
    Write-Info 'IMPROVED' $ImprovedRecords.Count
    Write-Info 'ACCEPTED' $AcceptedRecords.Count
    Write-Info 'REJECTED' $RejectedRecords.Count
    Write-Info 'REGRESSIONS' $RegressionRecords.Count

    Write-Host ''
    Write-Host 'SOURCE MUTATION         : 0' -ForegroundColor Green
    Write-Host 'EXECUTION              : DISABLED' -ForegroundColor Green
    Write-Host 'PROMOTION              : DISABLED' -ForegroundColor Green
    Write-Host 'CERTIFIED              : NOT AUTHORIZED' -ForegroundColor Yellow

    Write-Host ''
    Write-Info 'WORKBENCH' $Workbench
    Write-Info 'ACCEPTED CANDIDATES' $AcceptedRoot
    Write-Info 'EVIDENCE' $EvidencePath
    Write-Info 'REPORT' $ReportPath
    Write-Info 'MANIFEST' $ManifestPath

    Write-Host ''
    Write-Host "VERDICT : $GlobalVerdict" -ForegroundColor Cyan

    Write-Host ''
    Write-Host 'FAIL-CLOSED : les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun candidat n''est promu automatiquement.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun code candidat n''est exécuté.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ''
    Write-Host 'La fenêtre reste ouverte.' -ForegroundColor DarkGray
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer'
}
catch {

    $FatalMessage = $_.Exception.Message
    $InvariantFailure = $true

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v6.0.0 FAILED / FAIL-CLOSED' -ForegroundColor Red
    Write-Host '============================================================================' -ForegroundColor Red

    Write-Host ''
    Write-Host "ERROR : $FatalMessage" -ForegroundColor Red
    Write-Host ''

    Write-Host "SOURCE MUTATION : $SourceMutation"
    Write-Host "EXECUTION       : $ExecutionPerformed"
    Write-Host "PROMOTION       : $PromotionPerformed"

    Write-Host ''
    Write-Host 'Aucune promotion de candidat.' -ForegroundColor Yellow
    Write-Host 'Aucun CERTIFIED autorisé.' -ForegroundColor Yellow
    Write-Host 'Les sources originales restent intactes.' -ForegroundColor Yellow

    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''
    Read-Host 'Appuie sur ENTREE pour terminer'
}