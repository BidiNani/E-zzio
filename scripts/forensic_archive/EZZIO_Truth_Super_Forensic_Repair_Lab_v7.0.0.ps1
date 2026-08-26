#requires -Version 7.0

<#
===============================================================================
 E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v7.0.0
===============================================================================

MODE
    READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED

GARANTIES
    - Les sources originales ne sont jamais modifiées.
    - Aucun candidat n'est exécuté.
    - Aucun candidat n'est promu.
    - Aucun CERTIFIED n'est attribué.
    - Chaque transformation est isolée dans son propre candidat.
    - Chaque candidat est comparé au baseline parser du fichier concerné.
    - Toute régression est rejetée.
    - Toute ambiguïté est rejetée.
    - Les transformations sont déterministes.
    - Les résultats sont conservés comme preuves.

OBJECTIF
    Identifier des transformations syntaxiques mécaniques réellement
    améliorantes sans jamais toucher au projet réel.

===============================================================================
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# =============================================================================
# CONFIGURATION
# =============================================================================

$EngineName   = 'E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB'
$ScriptVersion = '7.0.0'

$ProjectRoot = 'G:\AI\E-zzio'

$TruthRoot = Join-Path $ProjectRoot '_EZZIO_TRUTH_REPORTS'

$SourceMutation      = $false
$ExecutionPerformed  = $false
$PromotionPerformed  = $false
$Certified           = $false
$CertifiedAuthorized = $false

# =============================================================================
# OUTILS DE BASE
# =============================================================================

function Write-Banner {
    param(
        [string]$Text,
        [ConsoleColor]$Color = [ConsoleColor]::Green
    )

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor $Color
    Write-Host $Text -ForegroundColor $Color
    Write-Host '============================================================================' -ForegroundColor $Color
}

function Write-Step {
    param(
        [string]$Number,
        [string]$Text
    )

    Write-Host ''
    Write-Host "[$Number] $Text..." -ForegroundColor Cyan
}

function Write-Info {
    param(
        [string]$Name,
        [object]$Value
    )

    Write-Host ("      {0,-28}: {1}" -f $Name,$Value)
}

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

        [AllowNull()]
        [string]$Content
    )

    if ($null -eq $Content) {
        $Content = ''
    }

    $utf8 = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path,$Content,$utf8)
}

function Read-Utf8 {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return [System.IO.File]::ReadAllText(
        $Path,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Get-Sha256 {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function New-RunId {
    $stamp = [DateTime]::UtcNow.ToString(
        'yyyyMMdd_HHmmss_fff',
        [System.Globalization.CultureInfo]::InvariantCulture
    )

    $entropy = [Guid]::NewGuid().ToString('N').Substring(0,12)

    return '{0}_{1}' -f $stamp,$entropy
}

function Get-ObjectProperty {
    param(
        [AllowNull()]
        [object]$Object,

        [Parameter(Mandatory)]
        [string]$Name,

        [AllowNull()]
        [object]$Default = $null
    )

    if ($null -eq $Object) {
        return $Default
    }

    $property = $Object.PSObject.Properties[$Name]

    if ($null -eq $property) {
        return $Default
    }

    return $property.Value
}

# =============================================================================
# SELF PARSER
# =============================================================================

function Get-PowerShellParserErrors {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $tokens = $null
    $parseErrors = $null

    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref]$tokens,
        [ref]$parseErrors
    )

    $records = [System.Collections.Generic.List[object]]::new()

    foreach ($parseErrorRecord in @($parseErrors)) {

        if ($null -eq $parseErrorRecord) {
            continue
        }

        $extent = $parseErrorRecord.Extent

        $records.Add(
            [pscustomobject]@{
                File        = $Path
                Message     = [string]$parseErrorRecord.Message
                ErrorId     = [string]$parseErrorRecord.ErrorId
                StartLine   = [int]$extent.StartLineNumber
                StartColumn = [int]$extent.StartColumnNumber
                EndLine     = [int]$extent.EndLineNumber
                EndColumn   = [int]$extent.EndColumnNumber
                Text        = [string]$extent.Text
            }
        )
    }

    return @($records)
}

function Test-PowerShellSyntax {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $errors = @(Get-PowerShellParserErrors -Path $Path)

    return [pscustomobject]@{
        Valid  = ($errors.Count -eq 0)
        Errors = $errors
        Count  = $errors.Count
    }
}

# =============================================================================
# MATRIX / DOSSIER DISCOVERY
# =============================================================================

function Find-LatestRepairDossier {

    if (-not (Test-Path -LiteralPath $TruthRoot -PathType Container)) {
        throw "Truth root absent : $TruthRoot"
    }

    $dirs = @(
        Get-ChildItem `
            -LiteralPath $TruthRoot `
            -Directory `
            -ErrorAction Stop |
        Sort-Object LastWriteTimeUtc -Descending
    )

    foreach ($dir in $dirs) {

        $candidate = Join-Path $dir.FullName 'REPAIR_DOSSIER'

        if (-not (Test-Path -LiteralPath $candidate -PathType Container)) {
            continue
        }

        $matrix = Join-Path $candidate 'ROOT_CAUSE_MATRIX.json'

        if (Test-Path -LiteralPath $matrix -PathType Leaf) {
            return $candidate
        }
    }

    throw 'Aucun REPAIR_DOSSIER exploitable trouvé.'
}

function Load-RootCauseMatrix {
    param(
        [Parameter(Mandatory)]
        [string]$RepairDossier
    )

    $matrixPath = Join-Path $RepairDossier 'ROOT_CAUSE_MATRIX.json'

    if (-not (Test-Path -LiteralPath $matrixPath -PathType Leaf)) {
        throw "ROOT_CAUSE_MATRIX.json absent : $matrixPath"
    }

    $raw = Read-Utf8 -Path $matrixPath

    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw "ROOT_CAUSE_MATRIX.json est vide."
    }

    $data = $raw | ConvertFrom-Json

    return [pscustomobject]@{
        Path    = $matrixPath
        Data    = $data
        Records = @(Get-ObjectProperty -Object $data -Name 'RootCauses' -Default @())
    }
}

# =============================================================================
# EXTRACTION ROBUSTE DES CHEMINS
# =============================================================================

function Resolve-TargetFiles {
    param(
        [Parameter(Mandatory)]
        [object]$MatrixData
    )

    $found = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase
    )

    $paths = [System.Collections.Generic.List[string]]::new()

    function Add-PathCandidate {
        param(
            [AllowNull()]
            [object]$Value
        )

        if ($null -eq $Value) {
            return
        }

        $text = [string]$Value

        if ([string]::IsNullOrWhiteSpace($text)) {
            return
        }

        $text = $text.Trim()

        if (-not (
            $text.EndsWith('.ps1',[StringComparison]::OrdinalIgnoreCase) -or
            $text.EndsWith('.psm1',[StringComparison]::OrdinalIgnoreCase) -or
            $text.EndsWith('.psd1',[StringComparison]::OrdinalIgnoreCase)
        )) {
            return
        }

        $resolved = $null

        try {
            if ([System.IO.Path]::IsPathRooted($text)) {
                $resolved = $text
            }
            else {
                $resolved = Join-Path $ProjectRoot $text
            }
        }
        catch {
            return
        }

        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            return
        }

        try {
            $full = [System.IO.Path]::GetFullPath($resolved)
        }
        catch {
            return
        }

        if ($found.Add($full)) {
            $paths.Add($full)
        }
    }

    $queue = [System.Collections.Generic.Queue[object]]::new()
    $queue.Enqueue($MatrixData)

    while ($queue.Count -gt 0) {

        $current = $queue.Dequeue()

        if ($null -eq $current) {
            continue
        }

        if ($current -is [string]) {
            Add-PathCandidate $current
            continue
        }

        if ($current -is [System.Collections.IEnumerable] -and
            $current -isnot [string]) {

            foreach ($item in $current) {
                if ($null -ne $item) {
                    $queue.Enqueue($item)
                }
            }

            continue
        }

        foreach ($property in $current.PSObject.Properties) {

            if ($null -eq $property.Value) {
                continue
            }

            if ($property.Value -is [string]) {
                Add-PathCandidate $property.Value
            }
            else {
                $queue.Enqueue($property.Value)
            }
        }
    }

    return @($paths | Sort-Object)
}

# =============================================================================
# CANDIDATE TRANSFORMATIONS
# =============================================================================

function New-Strategy {
    param(
        [string]$Id,
        [string]$Description,
        [scriptblock]$Transform
    )

    return [pscustomobject]@{
        Id          = $Id
        Description = $Description
        Transform   = $Transform
    }
}

function Get-Strategies {

    $strategies = [System.Collections.Generic.List[object]]::new()

    # -------------------------------------------------------------------------
    # 1. SMART QUOTES
    # -------------------------------------------------------------------------

    $strategies.Add(
        (New-Strategy `
            -Id 'SMART_QUOTES' `
            -Description 'Remplacement des guillemets typographiques par ASCII' `
            -Transform {

                param([string]$Text)

                $result = $Text

                $result = $result.Replace([string][char]0x2018,[string][char]0x27)
                $result = $result.Replace([string][char]0x2019,[string][char]0x27)
                $result = $result.Replace([string][char]0x201C,[string][char]0x22)
                $result = $result.Replace([string][char]0x201D,[string][char]0x22)

                return $result
            }
        )
    )

    # -------------------------------------------------------------------------
    # 2. UNICODE DASHES
    # -------------------------------------------------------------------------

    $strategies.Add(
        (New-Strategy `
            -Id 'UNICODE_DASHES' `
            -Description 'Normalisation des tirets Unicode' `
            -Transform {

                param([string]$Text)

                $result = $Text

                foreach ($code in @(0x2010,0x2011,0x2012,0x2013,0x2014,0x2212)) {
                    $result = $result.Replace(
                        [string][char]$code,
                        '-'
                    )
                }

                return $result
            }
        )
    )

    # -------------------------------------------------------------------------
    # 3. INVISIBLE CHARACTERS
    # -------------------------------------------------------------------------

    $strategies.Add(
        (New-Strategy `
            -Id 'INVISIBLE_CHARS' `
            -Description 'Suppression de certains caractères Unicode invisibles' `
            -Transform {

                param([string]$Text)

                $result = $Text

                foreach ($code in @(0x200B,0x200C,0x200D,0x2060,0xFEFF)) {
                    $result = $result.Replace(
                        [string][char]$code,
                        ''
                    )
                }

                return $result
            }
        )
    )

    # -------------------------------------------------------------------------
    # 4. NUL CHARACTERS
    # -------------------------------------------------------------------------

    $strategies.Add(
        (New-Strategy `
            -Id 'NUL_CHARS' `
            -Description 'Suppression des caractères NUL' `
            -Transform {

                param([string]$Text)

                return $Text.Replace(
                    [string][char]0,
                    ''
                )
            }
        )
    )

    # -------------------------------------------------------------------------
    # 5. MARKDOWN FENCES
    # -------------------------------------------------------------------------

    $strategies.Add(
        (New-Strategy `
            -Id 'MARKDOWN_FENCES' `
            -Description 'Suppression prudente des fences Markdown seules' `
            -Transform {

                param([string]$Text)

                $lines = [System.Collections.Generic.List[string]]::new()

                foreach ($line in ($Text -split "`n",-1)) {

                    $trim = $line.Trim()

                    if ($trim -eq '```' -or
                        $trim -eq '```powershell' -or
                        $trim -eq '```pwsh') {
                        continue
                    }

                    $lines.Add($line.TrimEnd("`r"))
                }

                return ($lines -join "`n")
            }
        )
    )

    # -------------------------------------------------------------------------
    # 6. CONSOLE PROMPTS
    # -------------------------------------------------------------------------

    $strategies.Add(
        (New-Strategy `
            -Id 'CONSOLE_PROMPTS' `
            -Description 'Suppression de prompts PowerShell au début des lignes' `
            -Transform {

                param([string]$Text)

                $lines = [System.Collections.Generic.List[string]]::new()

                foreach ($line in ($Text -split "`n",-1)) {

                    $normalized = $line.TrimEnd("`r")

                    if ($normalized -match '^\s*PS\s+[^>]+>\s?(.*)$') {
                        $lines.Add($Matches[1])
                    }
                    elseif ($normalized -match '^\s*>>\s?(.*)$') {
                        $lines.Add($Matches[1])
                    }
                    else {
                        $lines.Add($normalized)
                    }
                }

                return ($lines -join "`n")
            }
        )
    )

    # -------------------------------------------------------------------------
    # 7. TRANSCRIPT MARKERS
    # -------------------------------------------------------------------------

    $strategies.Add(
        (New-Strategy `
            -Id 'TRANSCRIPT_MARKERS' `
            -Description 'Suppression de marqueurs de transcript évidents' `
            -Transform {

                param([string]$Text)

                $lines = [System.Collections.Generic.List[string]]::new()

                foreach ($line in ($Text -split "`n",-1)) {

                    $normalized = $line.TrimEnd("`r")

                    if ($normalized -match '^\s*Appuie sur ENTREE pour terminer') {
                        continue
                    }

                    if ($normalized -match '^\s*============================================================================\s*$') {
                        continue
                    }

                    $lines.Add($normalized)
                }

                return ($lines -join "`n")
            }
        )
    )

    # -------------------------------------------------------------------------
    # 8. LINE ENDINGS
    # -------------------------------------------------------------------------

    $strategies.Add(
        (New-Strategy `
            -Id 'LINE_ENDINGS' `
            -Description 'Normalisation déterministe des fins de ligne' `
            -Transform {

                param([string]$Text)

                $result = $Text.Replace("`r`n","`n")
                $result = $result.Replace("`r","`n")

                return $result
            }
        )
    )

    # -------------------------------------------------------------------------
    # 9. BACKTICK TRAILING WHITESPACE
    # -------------------------------------------------------------------------

    $strategies.Add(
        (New-Strategy `
            -Id 'BACKTICK_WHITESPACE' `
            -Description 'Suppression des espaces après backtick de continuation' `
            -Transform {

                param([string]$Text)

                $lines = [System.Collections.Generic.List[string]]::new()

                foreach ($line in ($Text -split "`n",-1)) {

                    $normalized = $line.TrimEnd("`r")

                    $normalized = [regex]::Replace(
                        $normalized,
                        '`[ \t]+$',
                        '`'
                    )

                    $lines.Add($normalized)
                }

                return ($lines -join "`n")
            }
        )
    )

    return @($strategies)
}

# =============================================================================
# APPLICATION D'UNE STRATEGIE
# =============================================================================

function Apply-Strategy {
    param(
        [Parameter(Mandatory)]
        [string]$SourcePath,

        [Parameter(Mandatory)]
        [string]$DestinationPath,

        [Parameter(Mandatory)]
        [object]$Strategy
    )

    $original = Read-Utf8 -Path $SourcePath

    $trial = & $Strategy.Transform $original

    if ($null -eq $trial) {
        throw "La stratégie $($Strategy.Id) a retourné NULL."
    }

    if ($trial -isnot [string]) {
        $trial = [string]$trial
    }

    Write-Utf8NoBom `
        -Path $DestinationPath `
        -Content $trial

    return [pscustomobject]@{
        OriginalLength = $original.Length
        TrialLength    = $trial.Length
        Changed        = ($original -cne $trial)
    }
}

# =============================================================================
# COMPARAISON
# =============================================================================

function Get-ParserScore {
    param(
        [int]$ErrorCount
    )

    # Plus bas = meilleur.
    return [int]$ErrorCount
}

function Compare-Candidate {
    param(
        [Parameter(Mandatory)]
        [int]$BaselineErrors,

        [Parameter(Mandatory)]
        [int]$CandidateErrors
    )

    $delta = $BaselineErrors - $CandidateErrors

    if ($CandidateErrors -lt $BaselineErrors) {
        return 'IMPROVED'
    }

    if ($CandidateErrors -gt $BaselineErrors) {
        return 'REGRESSION'
    }

    return 'NO_CHANGE'
}

# =============================================================================
# MAIN
# =============================================================================

$RunId = New-RunId

$Workbench = $null
$Reports = $null
$Evidence = $null
$AcceptedRoot = $null

$SourceMutation = $false
$ExecutionPerformed = $false
$PromotionPerformed = $false

try {

    Write-Banner "$EngineName v$ScriptVersion"

    Write-Info 'PROJECT' $ProjectRoot
    Write-Info 'MODE' 'READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED'
    Write-Info 'QUALITY' 'FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
    Write-Info 'SOURCE MUTATION' 'DISABLED'
    Write-Info 'EXECUTION' 'DISABLED'
    Write-Info 'PROMOTION' 'DISABLED'

    # -------------------------------------------------------------------------
    # 1
    # -------------------------------------------------------------------------

    Write-Step '1/20' 'Validation environnement'

    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw "Projet absent : $ProjectRoot"
    }

    $psVersion = $PSVersionTable.PSVersion.ToString()

    Write-Info 'POWERSHELL' $psVersion
    Write-Host '      ENVIRONMENT : PASS' -ForegroundColor Green

    # -------------------------------------------------------------------------
    # 2 SELF PARSER
    # -------------------------------------------------------------------------

    Write-Step '2/20' 'Auto-validation syntaxique du moteur'

    $self = Test-PowerShellSyntax -Path $PSCommandPath

    Write-Info 'SELF PARSER ERRORS' $self.Count

    if (-not $self.Valid) {
        throw "Le moteur v$ScriptVersion possède $($self.Count) erreur(s) parser."
    }

    Write-Host '      SELF PARSER : PASS' -ForegroundColor Green

    # -------------------------------------------------------------------------
    # 3
    # -------------------------------------------------------------------------

    Write-Step '3/20' 'Recherche du dernier REPAIR_DOSSIER'

    $RepairDossier = Find-LatestRepairDossier

    $MatrixPath = Join-Path $RepairDossier 'ROOT_CAUSE_MATRIX.json'

    Write-Info 'DOSSIER' $RepairDossier
    Write-Info 'MATRIX' $MatrixPath
    Write-Host '      DISCOVERY : PASS' -ForegroundColor Green

    # -------------------------------------------------------------------------
    # 4
    # -------------------------------------------------------------------------

    Write-Step '4/20' 'Chargement de la Root-Cause Matrix'

    $matrixInfo = Load-RootCauseMatrix -RepairDossier $RepairDossier

    $rootRecords = @($matrixInfo.Records)

    if ($rootRecords.Count -eq 0) {
        throw 'La Root-Cause Matrix ne contient aucune cause racine exploitable.'
    }

    Write-Info 'ROOT CAUSES' $rootRecords.Count

    # -------------------------------------------------------------------------
    # 5
    # -------------------------------------------------------------------------

    Write-Step '5/20' 'Identification forensic des fichiers cibles'

    $targetFiles = @(Resolve-TargetFiles -MatrixData $matrixInfo.Data)

    if ($targetFiles.Count -eq 0) {
        throw 'Aucun fichier PowerShell cible identifiable dans la Root-Cause Matrix.'
    }

    Write-Info 'TARGET FILES' $targetFiles.Count

    # -------------------------------------------------------------------------
    # 6
    # -------------------------------------------------------------------------

    Write-Step '6/20' 'Création du laboratoire forensic'

    $runRoot = Join-Path $TruthRoot $RunId

    $Workbench = Join-Path `
        $runRoot `
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

    $Reports = Join-Path `
        $Workbench `
        'REPORTS'

    $Evidence = Join-Path `
        $Workbench `
        'EVIDENCE'

    Ensure-Directory $CandidatesRoot
    Ensure-Directory $AcceptedRoot
    Ensure-Directory $RejectedRoot
    Ensure-Directory $Reports
    Ensure-Directory $Evidence

    Write-Info 'RUN ID' $RunId
    Write-Info 'WORKBENCH' $Workbench
    Write-Host '      WORKBENCH : PASS' -ForegroundColor Green

    # -------------------------------------------------------------------------
    # 7 BASELINE
    # -------------------------------------------------------------------------

    Write-Step '7/20' 'Construction du baseline SHA-256 + parser original'

    $baselineRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($sourcePath in $targetFiles) {

        $parser = Test-PowerShellSyntax -Path $sourcePath

        $baselineRecords.Add(
            [pscustomobject]@{
                Path         = $sourcePath
                Sha256       = Get-Sha256 -Path $sourcePath
                Length       = (Get-Item -LiteralPath $sourcePath).Length
                ParserErrors = [int]$parser.Count
                Errors       = @($parser.Errors)
            }
        )
    }

    $baselineErrorCount = (
        @($baselineRecords) |
        ForEach-Object { [int]$_.ParserErrors } |
        Measure-Object -Sum
    ).Sum

    Write-Info 'BASELINE FILES' $baselineRecords.Count
    Write-Info 'PARSER ERRORS' $baselineErrorCount

    # -------------------------------------------------------------------------
    # 8 CLONAGE
    # -------------------------------------------------------------------------

    Write-Step '8/20' 'Clonage strict des sources'

    foreach ($record in @($baselineRecords)) {

        $relative = [System.IO.Path]::GetRelativePath(
            $ProjectRoot,
            $record.Path
        )

        $candidatePath = Join-Path `
            $CandidatesRoot `
            $relative

        $candidateParent = Split-Path `
            -Parent `
            $candidatePath

        Ensure-Directory $candidateParent

        Copy-Item `
            -LiteralPath $record.Path `
            -Destination $candidatePath `
            -Force

        $candidateHash = Get-Sha256 -Path $candidatePath

        if ($candidateHash -ne $record.Sha256) {
            throw "Échec clonage SHA-256 : $($record.Path)"
        }
    }

    Write-Info 'CLONED' $baselineRecords.Count

    # -------------------------------------------------------------------------
    # 9 CANDIDATE BASELINE
    # -------------------------------------------------------------------------

    Write-Step '9/20' 'Revalidation parser des candidats clonés'

    $candidateBaselineRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($record in @($baselineRecords)) {

        $relative = [System.IO.Path]::GetRelativePath(
            $ProjectRoot,
            $record.Path
        )

        $candidatePath = Join-Path `
            $CandidatesRoot `
            $relative

        $parser = Test-PowerShellSyntax -Path $candidatePath

        $candidateBaselineRecords.Add(
            [pscustomobject]@{
                OriginalPath = $record.Path
                CandidatePath = $candidatePath
                Sha256 = Get-Sha256 -Path $candidatePath
                ParserErrors = [int]$parser.Count
            }
        )
    }

    $candidateBaselineErrors = (
        @($candidateBaselineRecords) |
        ForEach-Object { [int]$_.ParserErrors } |
        Measure-Object -Sum
    ).Sum

    if ($candidateBaselineErrors -ne $baselineErrorCount) {
        throw 'Le clonage a modifié le baseline parser.'
    }

    Write-Info 'CANDIDATE BASELINE' $candidateBaselineErrors

    # -------------------------------------------------------------------------
    # 10 QUEUE
    # -------------------------------------------------------------------------

    Write-Step '10/20' 'Construction de la file des erreurs parser'

    $errorQueue = [System.Collections.Generic.List[object]]::new()

    foreach ($record in @($baselineRecords)) {

        foreach ($parseIssue in @($record.Errors)) {

            if ($null -eq $parseIssue) {
                continue
            }

            $errorQueue.Add(
                [pscustomobject]@{
                    QueueId      = $errorQueue.Count + 1
                    File         = $record.Path
                    Message      = [string]$parseIssue.Message
                    ErrorId      = [string]$parseIssue.ErrorId
                    StartLine    = [int]$parseIssue.StartLine
                    StartColumn  = [int]$parseIssue.StartColumn
                    EndLine      = [int]$parseIssue.EndLine
                    EndColumn    = [int]$parseIssue.EndColumn
                    Text         = [string]$parseIssue.Text
                }
            )
        }
    }

    Write-Info 'ERROR QUEUE' $errorQueue.Count

    # -------------------------------------------------------------------------
    # 11 STRATEGIES
    # -------------------------------------------------------------------------

    Write-Step '11/20' 'Chargement des stratégies de réparation'

    $strategies = @(Get-Strategies)

    Write-Info 'STRATEGIES' $strategies.Count

    foreach ($strategy in $strategies) {
        Write-Host "      - $($strategy.Id)" -ForegroundColor DarkGray
    }

    # -------------------------------------------------------------------------
    # 12 TARGETED STRATEGY APPLICATION
    # -------------------------------------------------------------------------

    Write-Step '12/20' 'Évaluation isolée des stratégies'

    $attempts = [System.Collections.Generic.List[object]]::new()

    foreach ($strategy in $strategies) {

        $strategyRoot = Join-Path `
            $CandidatesRoot `
            ("__STRATEGY__{0}" -f $strategy.Id)

        Ensure-Directory $strategyRoot

        $strategyBaselineTotal = 0
        $strategyFinalTotal = 0

        foreach ($record in @($baselineRecords)) {

            $relative = [System.IO.Path]::GetRelativePath(
                $ProjectRoot,
                $record.Path
            )

            $candidatePath = Join-Path `
                $strategyRoot `
                $relative

            $candidateParent = Split-Path -Parent $candidatePath

            Ensure-Directory $candidateParent

            $sourceCandidate = Join-Path `
                $CandidatesRoot `
                $relative

            Copy-Item `
                -LiteralPath $sourceCandidate `
                -Destination $candidatePath `
                -Force

            $beforeHash = Get-Sha256 -Path $candidatePath
            $beforeParser = Test-PowerShellSyntax -Path $candidatePath

            $strategyBaselineTotal += $beforeParser.Count

            try {

                $applyInfo = Apply-Strategy `
                    -SourcePath $candidatePath `
                    -DestinationPath $candidatePath `
                    -Strategy $strategy

                $afterHash = Get-Sha256 -Path $candidatePath
                $afterParser = Test-PowerShellSyntax -Path $candidatePath

                $strategyFinalTotal += $afterParser.Count

                $classification = Compare-Candidate `
                    -BaselineErrors $beforeParser.Count `
                    -CandidateErrors $afterParser.Count

                $attempts.Add(
                    [pscustomobject]@{
                        StrategyId          = $strategy.Id
                        StrategyDescription = $strategy.Description
                        OriginalPath        = $record.Path
                        CandidatePath       = $candidatePath
                        BeforeHash          = $beforeHash
                        AfterHash           = $afterHash
                        Changed             = [bool]$applyInfo.Changed
                        BeforeErrors        = [int]$beforeParser.Count
                        AfterErrors         = [int]$afterParser.Count
                        Improvement         = [int]($beforeParser.Count - $afterParser.Count)
                        Classification     = $classification
                        ErrorDetails        = @($afterParser.Errors)
                    }
                )
            }
            catch {

                $attempts.Add(
                    [pscustomobject]@{
                        StrategyId          = $strategy.Id
                        StrategyDescription = $strategy.Description
                        OriginalPath        = $record.Path
                        CandidatePath       = $candidatePath
                        BeforeHash          = $beforeHash
                        AfterHash           = $beforeHash
                        Changed             = $false
                        BeforeErrors        = [int]$beforeParser.Count
                        AfterErrors         = [int]$beforeParser.Count
                        Improvement         = 0
                        Classification     = 'STRATEGY_ERROR'
                        ErrorDetails        = @(
                            [pscustomobject]@{
                                Message = $_.Exception.Message
                            }
                        )
                    }
                )
            }
        }
    }

    Write-Info 'ATTEMPTS' $attempts.Count

    # -------------------------------------------------------------------------
    # 13 SELECTION
    # -------------------------------------------------------------------------

    Write-Step '13/20' 'Sélection stricte des améliorations'

    $improvedAttempts = @(
        $attempts |
        Where-Object {
            $_.Classification -eq 'IMPROVED' -and
            $_.AfterErrors -lt $_.BeforeErrors
        }
    )

    $regressionAttempts = @(
        $attempts |
        Where-Object {
            $_.Classification -eq 'REGRESSION'
        }
    )

    $noChangeAttempts = @(
        $attempts |
        Where-Object {
            $_.Classification -eq 'NO_CHANGE'
        }
    )

    Write-Info 'IMPROVED' $improvedAttempts.Count
    Write-Info 'REGRESSIONS' $regressionAttempts.Count
    Write-Info 'NO CHANGE' $noChangeAttempts.Count

    # -------------------------------------------------------------------------
    # 14 ACCEPTED CANDIDATES
    # -------------------------------------------------------------------------

    Write-Step '14/20' 'Archivage des candidats réellement améliorés'

    $acceptedRecords = [System.Collections.Generic.List[object]]::new()

    foreach ($attempt in $improvedAttempts) {

        $relative = [System.IO.Path]::GetRelativePath(
            $ProjectRoot,
            $attempt.OriginalPath
        )

        $safeStrategy = $attempt.StrategyId

        $destination = Join-Path `
            $AcceptedRoot `
            $safeStrategy

        $destination = Join-Path `
            $destination `
            $relative

        Ensure-Directory (Split-Path -Parent $destination)

        Copy-Item `
            -LiteralPath $attempt.CandidatePath `
            -Destination $destination `
            -Force

        $acceptedHash = Get-Sha256 -Path $destination

        $acceptedRecords.Add(
            [pscustomobject]@{
                StrategyId      = $attempt.StrategyId
                Strategy        = $attempt.StrategyDescription
                OriginalPath    = $attempt.OriginalPath
                CandidatePath   = $destination
                BeforeErrors    = $attempt.BeforeErrors
                AfterErrors     = $attempt.AfterErrors
                Improvement     = $attempt.Improvement
                CandidateSha256 = $acceptedHash
            }
        )
    }

    Write-Info 'ACCEPTED' $acceptedRecords.Count

    # -------------------------------------------------------------------------
    # 15 GLOBAL METRICS
    # -------------------------------------------------------------------------

    Write-Step '15/20' 'Calcul des métriques globales'

    if ($acceptedRecords.Count -gt 0) {

        $bestFinalErrors = (
            $acceptedRecords |
            ForEach-Object { [int]$_.AfterErrors } |
            Measure-Object -Minimum
        ).Minimum

        $globalImprovement = $baselineErrorCount - $bestFinalErrors

        if ($baselineErrorCount -gt 0) {
            $improvementRatio = (
                [Math]::Round(
                    ($globalImprovement / $baselineErrorCount) * 100,
                    2
                )
            )
        }
        else {
            $improvementRatio = 0
        }
    }
    else {

        $bestFinalErrors = $baselineErrorCount
        $globalImprovement = 0
        $improvementRatio = 0
    }

    if ($globalImprovement -gt 0) {
        $globalVerdict = 'IMPROVEMENT-FOUND / CANDIDATE-ONLY'
    }
    else {
        $globalVerdict = 'NO-IMPROVEMENT / FAIL-CLOSED'
    }

    Write-Info 'BEST FINAL ERRORS' $bestFinalErrors
    Write-Info 'GLOBAL IMPROVEMENT' $globalImprovement
    Write-Info 'IMPROVEMENT RATIO' "$improvementRatio %"
    Write-Info 'VERDICT' $globalVerdict

    # -------------------------------------------------------------------------
    # 16 SOURCE INTEGRITY
    # -------------------------------------------------------------------------

    Write-Step '16/20' 'Vérification absolue de l''intégrité des sources'

    $sourceMutations = [System.Collections.Generic.List[object]]::new()

    foreach ($record in @($baselineRecords)) {

        $currentHash = Get-Sha256 -Path $record.Path

        if ($currentHash -ne $record.Sha256) {

            $sourceMutations.Add(
                [pscustomobject]@{
                    Path     = $record.Path
                    Expected = $record.Sha256
                    Actual   = $currentHash
                }
            )
        }
    }

    if ($sourceMutations.Count -gt 0) {

        $SourceMutation = $true

        throw (
            'VIOLATION CRITIQUE : mutation détectée dans les sources originales.'
        )
    }

    Write-Info 'SOURCE MUTATIONS' 0
    Write-Host '      SOURCE INTEGRITY : PASS' -ForegroundColor Green

    # -------------------------------------------------------------------------
    # 17 EVIDENCE
    # -------------------------------------------------------------------------

    Write-Step '17/20' 'Génération des preuves forensic'

    $baselinePath = Join-Path `
        $Evidence `
        'BASELINE.json'

    $attemptsPath = Join-Path `
        $Evidence `
        'ALL_ATTEMPTS.json'

    $acceptedPath = Join-Path `
        $Evidence `
        'ACCEPTED_CANDIDATES.json'

    $errorsPath = Join-Path `
        $Evidence `
        'ERROR_QUEUE.json'

    $manifestPath = Join-Path `
        $Reports `
        'SUPER_FORENSIC_REPAIR_V7_MANIFEST.json'

    $reportPath = Join-Path `
        $Reports `
        'SUPER_FORENSIC_REPAIR_V7_REPORT.txt'

    @(
        $baselineRecords
    ) |
        ConvertTo-Json -Depth 30 |
        Set-Content -LiteralPath $baselinePath -Encoding utf8

    @(
        $attempts
    ) |
        ConvertTo-Json -Depth 30 |
        Set-Content -LiteralPath $attemptsPath -Encoding utf8

    @(
        $acceptedRecords
    ) |
        ConvertTo-Json -Depth 30 |
        Set-Content -LiteralPath $acceptedPath -Encoding utf8

    @(
        $errorQueue
    ) |
        ConvertTo-Json -Depth 30 |
        Set-Content -LiteralPath $errorsPath -Encoding utf8

    $manifest = [ordered]@{
        Engine                = $EngineName
        Version               = $ScriptVersion
        RunId                 = $RunId
        TimestampUtc          = [DateTime]::UtcNow.ToString('o')
        ProjectRoot           = $ProjectRoot
        RepairDossier         = $RepairDossier
        RootCauses            = $rootRecords.Count
        TargetFiles           = $targetFiles.Count
        BaselineParserErrors  = $baselineErrorCount
        BestFinalParserErrors = $bestFinalErrors
        GlobalImprovement     = $globalImprovement
        ImprovementRatio      = $improvementRatio
        Strategies            = $strategies.Count
        Attempts              = $attempts.Count
        AcceptedCandidates    = $acceptedRecords.Count
        Regressions           = $regressionAttempts.Count
        SourceMutation        = $SourceMutation
        ExecutionPerformed    = $ExecutionPerformed
        PromotionPerformed    = $PromotionPerformed
        Certified             = $Certified
        CertifiedAuthorized   = $CertifiedAuthorized
        Verdict               = $globalVerdict
    }

    $manifest |
        ConvertTo-Json -Depth 30 |
        Set-Content -LiteralPath $manifestPath -Encoding utf8

    # -------------------------------------------------------------------------
    # 18 REPORT
    # -------------------------------------------------------------------------

    Write-Step '18/20' 'Génération du rapport final'

    $reportLines = [System.Collections.Generic.List[string]]::new()

    $reportLines.Add('============================================================================')
    $reportLines.Add(' E-ZZIO — TRUTH SUPER FORENSIC REPAIR LAB v7.0.0')
    $reportLines.Add('============================================================================')
    $reportLines.Add('')
    $reportLines.Add("RUN ID                  : $RunId")
    $reportLines.Add("PROJECT                 : $ProjectRoot")
    $reportLines.Add("REPAIR DOSSIER          : $RepairDossier")
    $reportLines.Add('')
    $reportLines.Add("ROOT CAUSES             : $($rootRecords.Count)")
    $reportLines.Add("TARGET FILES            : $($targetFiles.Count)")
    $reportLines.Add("BASELINE PARSER ERRORS  : $baselineErrorCount")
    $reportLines.Add("BEST FINAL ERRORS       : $bestFinalErrors")
    $reportLines.Add("GLOBAL IMPROVEMENT      : $globalImprovement")
    $reportLines.Add("IMPROVEMENT RATIO       : $improvementRatio %")
    $reportLines.Add('')
    $reportLines.Add("STRATEGIES              : $($strategies.Count)")
    $reportLines.Add("ATTEMPTS                : $($attempts.Count)")
    $reportLines.Add("ACCEPTED                : $($acceptedRecords.Count)")
    $reportLines.Add("REGRESSIONS             : $($regressionAttempts.Count)")
    $reportLines.Add("NO CHANGE               : $($noChangeAttempts.Count)")
    $reportLines.Add('')
    $reportLines.Add("SOURCE MUTATION         : $SourceMutation")
    $reportLines.Add("EXECUTION              : $ExecutionPerformed")
    $reportLines.Add("PROMOTION              : $PromotionPerformed")
    $reportLines.Add("CERTIFIED              : $Certified")
    $reportLines.Add("CERTIFIED AUTHORIZED   : $CertifiedAuthorized")
    $reportLines.Add('')
    $reportLines.Add("VERDICT                : $globalVerdict")
    $reportLines.Add('')
    $reportLines.Add("WORKBENCH              : $Workbench")
    $reportLines.Add("ACCEPTED CANDIDATES    : $AcceptedRoot")
    $reportLines.Add("BASELINE               : $baselinePath")
    $reportLines.Add("ALL ATTEMPTS           : $attemptsPath")
    $reportLines.Add("ACCEPTED               : $acceptedPath")
    $reportLines.Add("ERROR QUEUE            : $errorsPath")
    $reportLines.Add("MANIFEST               : $manifestPath")
    $reportLines.Add('')
    $reportLines.Add('FAIL-CLOSED : les sources originales n''ont pas été modifiées.')
    $reportLines.Add('FAIL-CLOSED : aucun code candidat n''a été exécuté.')
    $reportLines.Add('FAIL-CLOSED : aucun candidat n''a été promu.')
    $reportLines.Add('FAIL-CLOSED : CERTIFIED n''est jamais attribué par ce moteur.')
    $reportLines.Add('============================================================================')

    Write-Utf8NoBom `
        -Path $reportPath `
        -Content ($reportLines -join [Environment]::NewLine)

    # -------------------------------------------------------------------------
    # 19 FINAL INTEGRITY OF EVIDENCE
    # -------------------------------------------------------------------------

    Write-Step '19/20' 'Vérification finale des artefacts forensic'

    $requiredArtifacts = @(
        $baselinePath,
        $attemptsPath,
        $acceptedPath,
        $errorsPath,
        $manifestPath,
        $reportPath
    )

    foreach ($artifact in $requiredArtifacts) {

        if (-not (Test-Path -LiteralPath $artifact -PathType Leaf)) {
            throw "Artefact forensic absent : $artifact"
        }

        $length = (Get-Item -LiteralPath $artifact).Length

        if ($length -lt 0) {
            throw "Taille artefact invalide : $artifact"
        }
    }

    Write-Info 'ARTIFACTS VERIFIED' $requiredArtifacts.Count
    Write-Host '      EVIDENCE : PASS' -ForegroundColor Green

    # -------------------------------------------------------------------------
    # 20 FINAL
    # -------------------------------------------------------------------------

    Write-Step '20/20' 'Gates finales'

    if ($SourceMutation) {
        throw 'GATE FAIL : source mutation.'
    }

    if ($ExecutionPerformed) {
        throw 'GATE FAIL : execution performed.'
    }

    if ($PromotionPerformed) {
        throw 'GATE FAIL : promotion performed.'
    }

    $Certified = $false
    $CertifiedAuthorized = $false

    Write-Host ''
    Write-Banner "$EngineName v$ScriptVersion COMPLETE" Green

    Write-Info 'RUN ID' $RunId
    Write-Info 'ROOT CAUSES' $rootRecords.Count
    Write-Info 'TARGET FILES' $targetFiles.Count
    Write-Info 'PARSER BASELINE' $baselineErrorCount
    Write-Info 'PARSER BEST' $bestFinalErrors
    Write-Info 'GLOBAL IMPROVEMENT' $globalImprovement
    Write-Info 'ATTEMPTS' $attempts.Count
    Write-Info 'ACCEPTED' $acceptedRecords.Count
    Write-Info 'REGRESSIONS' $regressionAttempts.Count

    Write-Host ''
    Write-Host 'SOURCE MUTATION         : 0' -ForegroundColor Green
    Write-Host 'EXECUTION              : DISABLED' -ForegroundColor Green
    Write-Host 'PROMOTION              : DISABLED' -ForegroundColor Green
    Write-Host 'CERTIFIED              : NOT AUTHORIZED' -ForegroundColor Yellow

    Write-Host ''
    Write-Info 'WORKBENCH' $Workbench
    Write-Info 'ACCEPTED CANDIDATES' $AcceptedRoot
    Write-Info 'REPORT' $reportPath
    Write-Info 'MANIFEST' $manifestPath
    Write-Info 'EVIDENCE' $attemptsPath

    Write-Host ''
    Write-Host "VERDICT : $globalVerdict" -ForegroundColor Cyan

    Write-Host ''
    Write-Host 'FAIL-CLOSED : les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun candidat n''est exécuté.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun candidat n''est promu.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer'
}
catch {

    Write-Host ''
    Write-Banner "$EngineName v$ScriptVersion FAILED / FAIL-CLOSED" Red

    Write-Host ''
    Write-Host "ERROR : $($_.Exception.Message)" -ForegroundColor Red

    if ($_.InvocationInfo) {
        Write-Host ''
        Write-Host "LINE : $($_.InvocationInfo.ScriptLineNumber)" -ForegroundColor DarkRed
        Write-Host "POSITION : $($_.InvocationInfo.OffsetInLine)" -ForegroundColor DarkRed
    }

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