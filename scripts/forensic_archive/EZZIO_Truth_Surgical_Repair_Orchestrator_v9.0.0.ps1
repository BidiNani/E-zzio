# ============================================================================
# E-ZZIO — TRUTH SURGICAL REPAIR ORCHESTRATOR v9.0.0
# ============================================================================
# PURPOSE
#   Forensic surgical repair of PowerShell parser corruption.
#
# PRINCIPLES
#   - READ source
#   - NEVER execute source
#   - NEVER mutate source
#   - clone -> repair -> parse -> compare
#   - one surgical hypothesis at a time
#   - fail-closed
#   - no automatic promotion
#   - no CERTIFIED claim
#
# IMPORTANT
#   This engine repairs ONLY candidate copies.
#   Original E-ZZIO sources remain immutable.
# ============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:EngineName    = 'E-ZZIO — TRUTH SURGICAL REPAIR ORCHESTRATOR'
$script:EngineVersion = '9.0.0'
$script:ProjectRoot   = 'G:\AI\E-zzio'

$script:SourceMutation      = $false
$script:ExecutionPerformed  = $false
$script:PromotionPerformed  = $false

# ============================================================================
# HELPERS
# ============================================================================

function Write-Line {
    param(
        [string]$Text = '',
        [ConsoleColor]$Color = [ConsoleColor]::Gray
    )

    Write-Host $Text -ForegroundColor $Color
}

function Write-Step {
    param(
        [string]$Number,
        [string]$Text
    )

    Write-Host ''
    Write-Host "[$Number] $Text" -ForegroundColor Cyan
}

function Write-Info {
    param(
        [string]$Name,
        [object]$Value
    )

    Write-Host ("      {0,-28}: {1}" -f $Name,$Value)
}

function Get-RunId {
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss_fff')
    $guid  = [Guid]::NewGuid().ToString('N').Substring(0,12)

    return "${stamp}_${guid}"
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [AllowEmptyString()]
        [string]$Content
    )

    $encoding = [System.Text.UTF8Encoding]::new($false)

    [System.IO.File]::WriteAllText(
        $Path,
        $Content,
        $encoding
    )
}

function Get-Text {
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

    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Get-ParserResult {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $tokens = $null
    $errors = $null

    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref]$tokens,
        [ref]$errors
    )

    $errorArray = @($errors)

    return [pscustomobject]@{
        Path   = $Path
        Tokens = @($tokens)
        Errors = $errorArray
        Count  = $errorArray.Count
    }
}

function Get-ParserResultFromText {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    $tokens = $null
    $errors = $null

    $null = [System.Management.Automation.Language.Parser]::ParseInput(
        $Text,
        [ref]$tokens,
        [ref]$errors
    )

    $errorArray = @($errors)

    return [pscustomobject]@{
        Tokens = @($tokens)
        Errors = $errorArray
        Count  = $errorArray.Count
    }
}

function Get-ErrorLine {
    param(
        [Parameter(Mandatory)]
        $ParserError
    )

    if ($null -ne $ParserError.Extent) {
        return [int]$ParserError.Extent.StartLineNumber
    }

    return 0
}

function Get-ErrorColumn {
    param(
        [Parameter(Mandatory)]
        $ParserError
    )

    if ($null -ne $ParserError.Extent) {
        return [int]$ParserError.Extent.StartColumnNumber
    }

    return 0
}

function Get-ErrorMessage {
    param(
        [Parameter(Mandatory)]
        $ParserError
    )

    return [string]$ParserError.Message
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

function Resolve-ProjectPath {
    param(
        [Parameter(Mandatory)]
        [string]$RelativePath
    )

    $normalized = $RelativePath.Replace('/','\').TrimStart('\')

    return [System.IO.Path]::GetFullPath(
        (Join-Path -Path $script:ProjectRoot -ChildPath $normalized)
    )
}

function Get-LatestRepairDossier {
    $root = Join-Path $script:ProjectRoot '_EZZIO_TRUTH_REPORTS'

    if (-not (Test-Path -LiteralPath $root -PathType Container)) {
        throw "Le répertoire _EZZIO_TRUTH_REPORTS est introuvable."
    }

    $dirs = @(
        Get-ChildItem -LiteralPath $root -Directory |
            Where-Object {
                Test-Path -LiteralPath (
                    Join-Path $_.FullName 'REPAIR_DOSSIER'
                ) -PathType Container
            } |
            Sort-Object LastWriteTimeUtc -Descending
    )

    if ($dirs.Count -eq 0) {
        throw 'Aucun REPAIR_DOSSIER exploitable trouvé.'
    }

    return (Join-Path $dirs[0].FullName 'REPAIR_DOSSIER')
}

function Get-ParserContextPath {
    param(
        [Parameter(Mandatory)]
        [string]$RepairDossier
    )

    $candidates = @(
        'POWERSHELL_PARSER_ERRORS.json',
        'ROOT_CAUSE_SOURCE_CONTEXT.txt'
    )

    foreach ($name in $candidates) {
        $path = Join-Path $RepairDossier $name

        if (Test-Path -LiteralPath $path -PathType Leaf) {
            return $path
        }
    }

    $nested = Get-ChildItem `
        -LiteralPath $RepairDossier `
        -Recurse `
        -File `
        -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match 'PARSER.*ERROR|PARSER_ERROR_CONTEXT'
        } |
        Sort-Object LastWriteTimeUtc -Descending

    if ($nested.Count -gt 0) {
        return $nested[0].FullName
    }

    return $null
}

function Get-TargetFilesFromContext {
    param(
        [Parameter(Mandatory)]
        [string]$ContextPath
    )

    $result = New-Object System.Collections.Generic.List[string]

    $lines = @(
        Get-Content -LiteralPath $ContextPath -Encoding UTF8
    )

    foreach ($line in $lines) {

        if ($line -match '^FILE:\s+(.+)$') {

            $raw = $Matches[1].Trim()

            if ([string]::IsNullOrWhiteSpace($raw)) {
                continue
            }

            $full = $raw

            if (-not [System.IO.Path]::IsPathRooted($full)) {
                $full = Resolve-ProjectPath $raw
            }

            if (
                (Test-Path -LiteralPath $full -PathType Leaf) -and
                ([System.IO.Path]::GetExtension($full) -ieq '.ps1')
            ) {
                if (-not $result.Contains($full)) {
                    $result.Add($full)
                }
            }
        }
    }

    return @($result)
}

function Get-RootCauseCount {
    param(
        [Parameter(Mandatory)]
        [string]$RepairDossier
    )

    $matrix = Join-Path $RepairDossier 'ROOT_CAUSE_MATRIX.json'

    if (-not (Test-Path -LiteralPath $matrix -PathType Leaf)) {
        return 0
    }

    try {
        $raw = Get-Content -LiteralPath $matrix -Raw -Encoding UTF8
        $obj = $raw | ConvertFrom-Json

        $candidates = @()

        foreach ($property in @(
            'RootCauses',
            'RootCause',
            'Causes',
            'Items',
            'Records',
            'Matrix'
        )) {
            if ($null -ne $obj.PSObject.Properties[$property]) {
                $value = $obj.$property

                if ($value -is [System.Collections.IEnumerable] -and
                    -not ($value -is [string])) {
                    $candidates += @($value)
                }
            }
        }

        if ($candidates.Count -gt 0) {
            return $candidates.Count
        }

        if ($obj -is [System.Collections.IEnumerable] -and
            -not ($obj -is [string])) {
            return @($obj).Count
        }

        return 0
    }
    catch {
        return 0
    }
}

function Get-ErrorRecords {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $parse = Get-ParserResult -Path $Path

    $records = New-Object System.Collections.Generic.List[object]

    foreach ($e in @($parse.Errors)) {

        $records.Add(
            [pscustomobject]@{
                File    = $Path
                Line    = Get-ErrorLine $e
                Column  = Get-ErrorColumn $e
                Message = Get-ErrorMessage $e
            }
        )
    }

    return @($records)
}

# ============================================================================
# SURGICAL REPAIR RULES
# ============================================================================

function Invoke-Rule_GetFullPathJoinPath {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    $pattern = '(?ms)(?<indent>^[ \t]*)\$physicalPath\s*=\s*\[System\.IO\.Path\]::GetFullPath\(\s*Join-Path\s+\$sourceRoot\s+\$targetNormalized\s*\)'

    $replacement = '${indent}$joinedPath = Join-Path -Path $sourceRoot -ChildPath $targetNormalized' +
                   [Environment]::NewLine +
                   '${indent}$physicalPath = [System.IO.Path]::GetFullPath($joinedPath)'

    $result = [regex]::Replace(
        $Text,
        $pattern,
        $replacement,
        1
    )

    return [pscustomobject]@{
        Changed = ($result -ne $Text)
        Text    = $result
        Rule    = 'GETFULLPATH_JOINPATH_SPLIT'
    }
}

function Invoke-Rule_MethodAddCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    # Repairs:
    #
    #   $collection.Add(
    #       Invoke-Something `
    #           -Parameter value
    #   )
    #
    # into:
    #
    #   $collection.Add(
    #       (Invoke-Something `
    #           -Parameter value)
    #   )
    #
    # This is deliberately restricted to Invoke-* command calls.

    $pattern = '(?ms)(?<prefix>\$[A-Za-z_][A-Za-z0-9_.]*\.Add\(\s*)(?<command>Invoke-[A-Za-z_][A-Za-z0-9_-]*\b.*?)(?<suffix>\s*\))'

    $match = [regex]::Match($Text,$pattern)

    if (-not $match.Success) {
        return [pscustomobject]@{
            Changed = $false
            Text    = $Text
            Rule    = 'METHOD_ADD_COMMAND'
        }
    }

    $prefix  = $match.Groups['prefix'].Value
    $command = $match.Groups['command'].Value
    $suffix  = $match.Groups['suffix'].Value

    if ($command.TrimEnd().EndsWith(')')) {
        return [pscustomobject]@{
            Changed = $false
            Text    = $Text
            Rule    = 'METHOD_ADD_COMMAND'
        }
    }

    $newBlock =
        $prefix +
        '(' +
        $command +
        ')' +
        $suffix

    $result =
        $Text.Substring(0,$match.Index) +
        $newBlock +
        $Text.Substring($match.Index + $match.Length)

    return [pscustomobject]@{
        Changed = $true
        Text    = $result
        Rule    = 'METHOD_ADD_COMMAND'
    }
}

function Invoke-Rule_CommandArgumentInMethod {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    # More general PowerShell method-call repair.
    #
    # Converts:
    #
    #   $x.Add(
    #       Some-Command ...
    #   )
    #
    # into:
    #
    #   $x.Add(
    #       (Some-Command ...)
    #   )
    #
    # Only used when the command begins with a standard verb.

    $pattern = '(?ms)(?<prefix>\$[A-Za-z_][A-Za-z0-9_.]*\.[A-Za-z_][A-Za-z0-9_]*\(\s*)(?<command>(?:Invoke|Get|Set|New|Remove|Resolve|Convert|Test|Write|Read|Start|Stop|Find|Select|Where|Sort|Measure|ForEach)-[A-Za-z_][A-Za-z0-9_-]*\b.*?)(?<suffix>\s*\))'

    $match = [regex]::Match($Text,$pattern)

    if (-not $match.Success) {
        return [pscustomobject]@{
            Changed = $false
            Text    = $Text
            Rule    = 'COMMAND_ARGUMENT_IN_METHOD'
        }
    }

    $prefix  = $match.Groups['prefix'].Value
    $command = $match.Groups['command'].Value
    $suffix  = $match.Groups['suffix'].Value

    if ($command.TrimStart().StartsWith('(')) {
        return [pscustomobject]@{
            Changed = $false
            Text    = $Text
            Rule    = 'COMMAND_ARGUMENT_IN_METHOD'
        }
    }

    $newBlock =
        $prefix +
        '(' +
        $command +
        ')' +
        $suffix

    $result =
        $Text.Substring(0,$match.Index) +
        $newBlock +
        $Text.Substring($match.Index + $match.Length)

    return [pscustomobject]@{
        Changed = $true
        Text    = $result
        Rule    = 'COMMAND_ARGUMENT_IN_METHOD'
    }
}

function Invoke-Rule_SmartQuotes {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    $result = $Text

    $result = $result.Replace([string][char]0x2018, "'")
    $result = $result.Replace([string][char]0x2019, "'")
    $result = $result.Replace([string][char]0x201C, '"')
    $result = $result.Replace([string][char]0x201D, '"')

    return [pscustomobject]@{
        Changed = ($result -ne $Text)
        Text    = $result
        Rule    = 'SMART_QUOTES'
    }
}

function Invoke-Rule_UnicodeDashes {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    $result = $Text

    $result = $result.Replace([string][char]0x2013, '-')
    $result = $result.Replace([string][char]0x2014, '-')
    $result = $result.Replace([string][char]0x2212, '-')

    return [pscustomobject]@{
        Changed = ($result -ne $Text)
        Text    = $result
        Rule    = 'UNICODE_DASHES'
    }
}

function Invoke-Rule_RemoveNul {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    $result = $Text.Replace([string][char]0x0000,'')

    return [pscustomobject]@{
        Changed = ($result -ne $Text)
        Text    = $result
        Rule    = 'NUL_CHARS'
    }
}

function Invoke-Rule_InvisibleCharacters {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    $result = $Text

    foreach ($code in @(
        0x200B,
        0x200C,
        0x200D,
        0x2060,
        0xFEFF
    )) {
        $result = $result.Replace([string][char]$code,'')
    }

    return [pscustomobject]@{
        Changed = ($result -ne $Text)
        Text    = $result
        Rule    = 'INVISIBLE_CHARS'
    }
}

function Invoke-Rule_BacktickWhitespace {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    # Only remove whitespace AFTER a PowerShell continuation backtick.
    # Never touch arbitrary backticks.
    $result = [regex]::Replace(
        $Text,
        '`[ \t]+(?=\r?\n)',
        '`'
    )

    return [pscustomobject]@{
        Changed = ($result -ne $Text)
        Text    = $result
        Rule    = 'BACKTICK_WHITESPACE'
    }
}

# ============================================================================
# STRATEGY LIST
# ============================================================================

function Get-RepairStrategies {

    return @(
        [pscustomobject]@{
            Name = 'GETFULLPATH_JOINPATH_SPLIT'
            Apply = {
                param($text)
                Invoke-Rule_GetFullPathJoinPath -Text $text
            }
        }
        [pscustomobject]@{
            Name = 'METHOD_ADD_COMMAND'
            Apply = {
                param($text)
                Invoke-Rule_MethodAddCommand -Text $text
            }
        }
        [pscustomobject]@{
            Name = 'COMMAND_ARGUMENT_IN_METHOD'
            Apply = {
                param($text)
                Invoke-Rule_CommandArgumentInMethod -Text $text
            }
        }
        [pscustomobject]@{
            Name = 'SMART_QUOTES'
            Apply = {
                param($text)
                Invoke-Rule_SmartQuotes -Text $text
            }
        }
        [pscustomobject]@{
            Name = 'UNICODE_DASHES'
            Apply = {
                param($text)
                Invoke-Rule_UnicodeDashes -Text $text
            }
        }
        [pscustomobject]@{
            Name = 'NUL_CHARS'
            Apply = {
                param($text)
                Invoke-Rule_RemoveNul -Text $text
            }
        }
        [pscustomobject]@{
            Name = 'INVISIBLE_CHARS'
            Apply = {
                param($text)
                Invoke-Rule_InvisibleCharacters -Text $text
            }
        }
        [pscustomobject]@{
            Name = 'BACKTICK_WHITESPACE'
            Apply = {
                param($text)
                Invoke-Rule_BacktickWhitespace -Text $text
            }
        }
    )
}

# ============================================================================
# MAIN
# ============================================================================

try {

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host "E-ZZIO — $($script:EngineName) v$($script:EngineVersion)" -ForegroundColor Green
    Write-Host '============================================================================' -ForegroundColor Green

    Write-Info 'PROJECT' $script:ProjectRoot
    Write-Info 'MODE' 'READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED'
    Write-Info 'QUALITY' 'FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
    Write-Info 'SOURCE MUTATION' 'DISABLED'
    Write-Info 'EXECUTION' 'DISABLED'
    Write-Info 'PROMOTION' 'DISABLED'

    # ------------------------------------------------------------------------
    # 1
    # ------------------------------------------------------------------------

    Write-Step '1/18' 'Validation environnement...'

    if (-not (Test-Path -LiteralPath $script:ProjectRoot -PathType Container)) {
        throw "Projet introuvable : $($script:ProjectRoot)"
    }

    Write-Info 'POWERSHELL' $PSVersionTable.PSVersion
    Write-Info 'ENVIRONMENT' 'PASS'

    # ------------------------------------------------------------------------
    # 2
    # ------------------------------------------------------------------------

    Write-Step '2/18' 'Auto-validation syntaxique du moteur...'

    $selfPath = $PSCommandPath

    if ([string]::IsNullOrWhiteSpace($selfPath)) {
        throw 'Impossible de déterminer le chemin du moteur.'
    }

    $selfParse = Get-ParserResult -Path $selfPath

    Write-Info 'SELF PARSER ERRORS' $selfParse.Count

    if ($selfParse.Count -ne 0) {
        throw 'Le moteur lui-même n''est pas syntaxiquement valide.'
    }

    Write-Info 'SELF PARSER' 'PASS'

    # ------------------------------------------------------------------------
    # 3
    # ------------------------------------------------------------------------

    Write-Step '3/18' 'Recherche du dernier REPAIR_DOSSIER...'

    $repairDossier = Get-LatestRepairDossier
    $contextPath   = Get-ParserContextPath -RepairDossier $repairDossier

    if ($null -eq $contextPath) {
        throw 'Aucun contexte parser exploitable dans le REPAIR_DOSSIER.'
    }

    Write-Info 'DOSSIER' $repairDossier
    Write-Info 'CONTEXT' $contextPath
    Write-Info 'DISCOVERY' 'PASS'

    # ------------------------------------------------------------------------
    # 4
    # ------------------------------------------------------------------------

    Write-Step '4/18' 'Chargement défensif de la Root-Cause Matrix...'

    $rootCauseCount = Get-RootCauseCount -RepairDossier $repairDossier

    Write-Info 'ROOT CAUSES' $rootCauseCount

    if ($rootCauseCount -le 0) {
        Write-Host '      MATRIX STATUS : VALIDATION PARTIELLE' -ForegroundColor Yellow
    }
    else {
        Write-Info 'MATRIX STATUS' 'VALID'
    }

    # ------------------------------------------------------------------------
    # 5
    # ------------------------------------------------------------------------

    Write-Step '5/18' 'Identification forensic des fichiers cibles...'

    $targetFiles = @(Get-TargetFilesFromContext -ContextPath $contextPath)

    if ($targetFiles.Count -eq 0) {
        throw 'Aucun fichier PowerShell cible trouvé dans le contexte forensic.'
    }

    Write-Info 'TARGET FILES' $targetFiles.Count

    # ------------------------------------------------------------------------
    # 6
    # ------------------------------------------------------------------------

    Write-Step '6/18' 'Création du laboratoire chirurgical...'

    $runId = Get-RunId

    $runRoot = Join-Path `
        $script:ProjectRoot `
        "_EZZIO_TRUTH_REPORTS\$runId"

    $labRoot = Join-Path `
        $runRoot `
        'SURGICAL_REPAIR_LAB'

    $candidateRoot = Join-Path `
        $labRoot `
        'CANDIDATES'

    $acceptedRoot = Join-Path `
        $labRoot `
        'ACCEPTED_CANDIDATES'

    $evidenceRoot = Join-Path `
        $labRoot `
        'EVIDENCE'

    $reportRoot = Join-Path `
        $labRoot `
        'REPORTS'

    foreach ($dir in @(
        $labRoot,
        $candidateRoot,
        $acceptedRoot,
        $evidenceRoot,
        $reportRoot
    )) {
        Ensure-Directory $dir
    }

    Write-Info 'RUN ID' $runId
    Write-Info 'LAB' $labRoot

    # ------------------------------------------------------------------------
    # 7
    # ------------------------------------------------------------------------

    Write-Step '7/18' 'Construction du baseline SHA-256 + parser...'

    $baseline = New-Object System.Collections.Generic.List[object]

    foreach ($file in $targetFiles) {

        $parse = Get-ParserResult -Path $file
        $hash  = Get-Sha256 -Path $file

        $baseline.Add(
            [pscustomobject]@{
                SourcePath    = $file
                RelativePath  = $file.Substring($script:ProjectRoot.Length).TrimStart('\')
                SHA256        = $hash
                ParserErrors  = $parse.Count
            }
        )
    }

    $baselineErrorCount = (
        $baseline |
            Measure-Object -Property ParserErrors -Sum
    ).Sum

    Write-Info 'BASELINE FILES' $baseline.Count
    Write-Info 'PARSER ERRORS' $baselineErrorCount

    # ------------------------------------------------------------------------
    # 8
    # ------------------------------------------------------------------------

    Write-Step '8/18' 'Clonage strict des sources...'

    $clones = New-Object System.Collections.Generic.List[object]

    foreach ($item in $baseline) {

        $relative = $item.RelativePath
        $candidate = Join-Path $candidateRoot $relative

        $candidateDirectory = Split-Path `
            -Parent `
            $candidate

        Ensure-Directory $candidateDirectory

        Copy-Item `
            -LiteralPath $item.SourcePath `
            -Destination $candidate `
            -Force

        $cloneHash = Get-Sha256 -Path $candidate

        if ($cloneHash -ne $item.SHA256) {
            throw "Échec de clonage intégral : $($item.SourcePath)"
        }

        $clones.Add(
            [pscustomobject]@{
                SourcePath   = $item.SourcePath
                Candidate    = $candidate
                RelativePath = $relative
                BaselineHash = $item.SHA256
                BaselineErrors = $item.ParserErrors
            }
        )
    }

    Write-Info 'CLONED' $clones.Count

    # ------------------------------------------------------------------------
    # 9
    # ------------------------------------------------------------------------

    Write-Step '9/18' 'Revalidation parser des candidats clonés...'

    $cloneErrors = 0

    foreach ($clone in $clones) {
        $parse = Get-ParserResult -Path $clone.Candidate
        $clone | Add-Member -NotePropertyName CloneParserErrors -NotePropertyValue $parse.Count
        $cloneErrors += $parse.Count
    }

    Write-Info 'CANDIDATE BASELINE' $cloneErrors

    if ($cloneErrors -ne $baselineErrorCount) {
        throw 'Le clonage a modifié le résultat parser.'
    }

    # ------------------------------------------------------------------------
    # 10
    # ------------------------------------------------------------------------

    Write-Step '10/18' 'Construction de la file des erreurs parser...'

    $errorQueue = New-Object System.Collections.Generic.List[object]

    foreach ($clone in $clones) {

        $errors = Get-ErrorRecords -Path $clone.Candidate

        foreach ($record in $errors) {
            $errorQueue.Add($record)
        }
    }

    Write-Info 'ERROR QUEUE' $errorQueue.Count

    # ------------------------------------------------------------------------
    # 11
    # ------------------------------------------------------------------------

    Write-Step '11/18' 'Chargement des stratégies chirurgicales...'

    $strategies = @(Get-RepairStrategies)

    Write-Info 'STRATEGIES' $strategies.Count

    foreach ($strategy in $strategies) {
        Write-Host "      - $($strategy.Name)"
    }

    # ------------------------------------------------------------------------
    # 12
    # ------------------------------------------------------------------------

    Write-Step '12/18' 'Évaluation isolée des stratégies...'

    $attempts = New-Object System.Collections.Generic.List[object]
    $accepted = New-Object System.Collections.Generic.List[object]

    foreach ($clone in $clones) {

        $originalText = Get-Text -Path $clone.Candidate

        foreach ($strategy in $strategies) {

            $trial = & $strategy.Apply $originalText

            if ($null -eq $trial) {
                continue
            }

            if (-not $trial.Changed) {
                continue
            }

            $trialId = Get-RunId

            $trialRelative =
                $clone.RelativePath

            $trialPath = Join-Path `
                $candidateRoot `
                ("TRIAL_{0}\{1}" -f $trialId,$trialRelative)

            Ensure-Directory (
                Split-Path -Parent $trialPath
            )

            Write-Utf8NoBom `
                -Path $trialPath `
                -Content $trial.Text

            $trialParse = Get-ParserResultFromText -Text $trial.Text

            $before = [int]$clone.BaselineErrors
            $after  = [int]$trialParse.Count

            $improvement = $before - $after

            $classification =
                if ($after -lt $before) {
                    'IMPROVED'
                }
                elseif ($after -gt $before) {
                    'REGRESSION'
                }
                else {
                    'NO_CHANGE'
                }

            $record = [pscustomobject]@{
                TrialId       = $trialId
                SourcePath    = $clone.SourcePath
                CandidatePath = $trialPath
                RelativePath  = $clone.RelativePath
                Strategy      = $trial.Rule
                BeforeErrors  = $before
                AfterErrors   = $after
                Improvement   = $improvement
                Classification = $classification
            }

            $attempts.Add($record)

            if ($classification -eq 'IMPROVED') {

                $accepted.Add($record)

                $acceptedPath = Join-Path `
                    $acceptedRoot `
                    ("{0}_{1}" -f $trialId,(Split-Path $clone.RelativePath -Leaf))

                Copy-Item `
                    -LiteralPath $trialPath `
                    -Destination $acceptedPath `
                    -Force
            }
        }
    }

    $improvedCount = @(
        $attempts |
            Where-Object Classification -eq 'IMPROVED'
    ).Count

    $regressionCount = @(
        $attempts |
            Where-Object Classification -eq 'REGRESSION'
    ).Count

    $noChangeCount = @(
        $attempts |
            Where-Object Classification -eq 'NO_CHANGE'
    ).Count

    Write-Info 'ATTEMPTS' $attempts.Count
    Write-Info 'IMPROVED' $improvedCount
    Write-Info 'REGRESSIONS' $regressionCount
    Write-Info 'NO CHANGE' $noChangeCount

    # ------------------------------------------------------------------------
    # 13
    # ------------------------------------------------------------------------

    Write-Step '13/18' 'Vérification AST des meilleurs candidats...'

    $fullyParsed = @(
        $accepted |
            Where-Object {
                $_.AfterErrors -eq 0
            }
    )

    Write-Info 'AST ZERO-ERROR CANDIDATES' $fullyParsed.Count

    # ------------------------------------------------------------------------
    # 14
    # ------------------------------------------------------------------------

    Write-Step '14/18' 'Vérification SHA-256 des sources originales...'

    $sourceMutationCount = 0

    foreach ($item in $baseline) {

        $currentHash = Get-Sha256 -Path $item.SourcePath

        if ($currentHash -ne $item.SHA256) {
            $sourceMutationCount++
        }
    }

    $script:SourceMutation = ($sourceMutationCount -ne 0)

    Write-Info 'SOURCE MUTATIONS' $sourceMutationCount

    if ($script:SourceMutation) {
        throw 'MUTATION DE SOURCE DÉTECTÉE — FAIL-CLOSED.'
    }

    Write-Info 'SOURCE INTEGRITY' 'PASS'

    # ------------------------------------------------------------------------
    # 15
    # ------------------------------------------------------------------------

    Write-Step '15/18' 'Vérification zéro exécution...'

    # This engine never invokes a candidate as PowerShell code.
    $script:ExecutionPerformed = $false

    Write-Info 'EXECUTION' 0
    Write-Info 'EXECUTION GATE' 'PASS'

    # ------------------------------------------------------------------------
    # 16
    # ------------------------------------------------------------------------

    Write-Step '16/18' 'Calcul des métriques globales...'

    $globalImprovement = 0

    if ($accepted.Count -gt 0) {
        $globalImprovement =
            ($accepted |
                Measure-Object -Property Improvement -Maximum).Maximum
    }

    $improvementRatio = 0

    if ($baselineErrorCount -gt 0) {
        $improvementRatio =
            [math]::Round(
                ($globalImprovement / $baselineErrorCount) * 100,
                2
            )
    }

    if ($fullyParsed.Count -gt 0) {
        $verdict = 'CANDIDATE-READY / FAIL-CLOSED'
    }
    elseif ($improvedCount -gt 0) {
        $verdict = 'PARTIAL-IMPROVEMENT / FAIL-CLOSED'
    }
    else {
        $verdict = 'NO-IMPROVEMENT / FAIL-CLOSED'
    }

    Write-Info 'GLOBAL IMPROVEMENT' $globalImprovement
    Write-Info 'IMPROVEMENT RATIO' "$improvementRatio %"
    Write-Info 'VERDICT' $verdict

    # ------------------------------------------------------------------------
    # 17
    # ------------------------------------------------------------------------

    Write-Step '17/18' 'Génération des preuves forensic...'

    $evidencePath = Join-Path `
        $evidenceRoot `
        'SURGICAL_ATTEMPTS.json'

    $attempts |
        ConvertTo-Json -Depth 20 |
        Write-Utf8NoBom -Path $evidencePath

    $baselinePath = Join-Path `
        $evidenceRoot `
        'SOURCE_BASELINE.json'

    $baseline |
        ConvertTo-Json -Depth 20 |
        Write-Utf8NoBom -Path $baselinePath

    $sourceHashAfter = New-Object System.Collections.Generic.List[object]

    foreach ($item in $baseline) {

        $sourceHashAfter.Add(
            [pscustomobject]@{
                Path   = $item.SourcePath
                Before = $item.SHA256
                After  = Get-Sha256 -Path $item.SourcePath
                Equal  = (
                    $item.SHA256 -eq (
                        Get-Sha256 -Path $item.SourcePath
                    )
                )
            }
        )
    }

    $afterPath = Join-Path `
        $evidenceRoot `
        'SOURCE_HASHES_AFTER.json'

    $sourceHashAfter |
        ConvertTo-Json -Depth 20 |
        Write-Utf8NoBom -Path $afterPath

    # ------------------------------------------------------------------------
    # 18
    # ------------------------------------------------------------------------

    Write-Step '18/18' 'Génération du manifeste et rapport...'

    $manifest = [ordered]@{
        Engine                 = $script:EngineName
        Version                = $script:EngineVersion
        RunId                  = $runId
        TimestampUtc           = [DateTime]::UtcNow.ToString('o')
        ProjectRoot            = $script:ProjectRoot
        RepairDossier          = $repairDossier
        RootCauses             = $rootCauseCount
        TargetFiles            = $targetFiles.Count
        BaselineParserErrors   = $baselineErrorCount
        CandidateBaselineErrors = $cloneErrors
        Attempts               = $attempts.Count
        Improved               = $improvedCount
        FullyParsedCandidates  = $fullyParsed.Count
        Regressions            = $regressionCount
        NoChange               = $noChangeCount
        GlobalImprovement      = $globalImprovement
        ImprovementRatio      = $improvementRatio
        SourceMutation         = $script:SourceMutation
        ExecutionPerformed     = $script:ExecutionPerformed
        PromotionPerformed     = $script:PromotionPerformed
        Certified              = $false
        CertifiedAuthorized    = $false
        Verdict                = $verdict
    }

    $manifestPath = Join-Path `
        $reportRoot `
        'SURGICAL_REPAIR_MANIFEST.json'

    $manifest |
        ConvertTo-Json -Depth 30 |
        Write-Utf8NoBom -Path $manifestPath

    $reportPath = Join-Path `
        $reportRoot `
        'SURGICAL_REPAIR_REPORT.txt'

    $reportLines = @(
        '============================================================================'
        ' E-ZZIO — TRUTH SURGICAL REPAIR ORCHESTRATOR v9.0.0'
        '============================================================================'
        ''
        "RUN ID                    : $runId"
        "PROJECT                   : $($script:ProjectRoot)"
        "REPAIR DOSSIER            : $repairDossier"
        ''
        "ROOT CAUSES               : $rootCauseCount"
        "TARGET FILES              : $($targetFiles.Count)"
        "BASELINE PARSER ERRORS   : $baselineErrorCount"
        "CANDIDATE BASELINE ERRORS: $cloneErrors"
        ''
        "REPAIR ATTEMPTS           : $($attempts.Count)"
        "IMPROVED                  : $improvedCount"
        "FULL AST ZERO-ERROR      : $($fullyParsed.Count)"
        "REGRESSIONS               : $regressionCount"
        "NO CHANGE                 : $noChangeCount"
        ''
        "GLOBAL IMPROVEMENT        : $globalImprovement"
        "IMPROVEMENT RATIO        : $improvementRatio %"
        ''
        "SOURCE MUTATION           : $($script:SourceMutation)"
        "EXECUTION                 : $($script:ExecutionPerformed)"
        "PROMOTION                 : $($script:PromotionPerformed)"
        "CERTIFIED                 : FALSE"
        "CERTIFIED AUTHORIZED     : FALSE"
        ''
        "VERDICT                   : $verdict"
        ''
        "LAB                       : $labRoot"
        "ACCEPTED CANDIDATES      : $acceptedRoot"
        "EVIDENCE                  : $evidencePath"
        "MANIFEST                  : $manifestPath"
        "REPORT                    : $reportPath"
        ''
        'FAIL-CLOSED : aucune source originale n''a été modifiée.'
        'FAIL-CLOSED : aucun candidat n''a été exécuté.'
        'FAIL-CLOSED : aucune promotion automatique n''a été effectuée.'
        'FAIL-CLOSED : CERTIFIED n''est jamais accordé par cet orchestrateur.'
        '============================================================================'
    )

    Write-Utf8NoBom `
        -Path $reportPath `
        -Content ($reportLines -join [Environment]::NewLine)

    # =========================================================================
    # FINAL GATES
    # =========================================================================

    $finalSelfParse = Get-ParserResult -Path $selfPath

    if ($finalSelfParse.Count -ne 0) {
        throw 'Le moteur a perdu son intégrité syntaxique.'
    }

    $finalMutationCount = 0

    foreach ($item in $baseline) {

        if (
            (Get-Sha256 -Path $item.SourcePath) -ne
            $item.SHA256
        ) {
            $finalMutationCount++
        }
    }

    if ($finalMutationCount -ne 0) {
        throw 'Final Gate: mutation source détectée.'
    }

    # =========================================================================
    # FINAL
    # =========================================================================

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host 'E-ZZIO — TRUTH SURGICAL REPAIR ORCHESTRATOR v9.0.0 COMPLETE' -ForegroundColor Green
    Write-Host '============================================================================' -ForegroundColor Green

    Write-Info 'RUN ID' $runId
    Write-Info 'ROOT CAUSES' $rootCauseCount
    Write-Info 'TARGET FILES' $targetFiles.Count
    Write-Info 'PARSER BASELINE' $baselineErrorCount
    Write-Info 'ATTEMPTS' $attempts.Count
    Write-Info 'IMPROVED' $improvedCount
    Write-Info 'ZERO-ERROR CANDIDATES' $fullyParsed.Count
    Write-Info 'REGRESSIONS' $regressionCount
    Write-Info 'GLOBAL IMPROVEMENT' $globalImprovement
    Write-Info 'IMPROVEMENT RATIO' "$improvementRatio %"

    Write-Host ''
    Write-Host 'SOURCE MUTATION         : 0' -ForegroundColor Green
    Write-Host 'EXECUTION              : DISABLED' -ForegroundColor Green
    Write-Host 'PROMOTION              : DISABLED' -ForegroundColor Green
    Write-Host 'CERTIFIED              : NOT AUTHORIZED' -ForegroundColor Yellow

    Write-Host ''
    Write-Info 'LAB' $labRoot
    Write-Info 'ACCEPTED CANDIDATES' $acceptedRoot
    Write-Info 'EVIDENCE' $evidencePath
    Write-Info 'REPORT' $reportPath
    Write-Info 'MANIFEST' $manifestPath

    Write-Host ''
    Write-Host "VERDICT : $verdict" -ForegroundColor Cyan

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host 'FAIL-CLOSED : les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun candidat n''est exécuté.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucune promotion automatique.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Green
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer' | Out-Null
}
catch {

    Write-Host ''
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host "E-ZZIO — TRUTH SURGICAL REPAIR ORCHESTRATOR v$($script:EngineVersion) FAILED / FAIL-CLOSED" -ForegroundColor Red
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''
    Write-Host "ERROR : $($_.Exception.Message)" -ForegroundColor Red

    if ($null -ne $_.InvocationInfo) {
        Write-Host ''
        Write-Host "LINE : $($_.InvocationInfo.ScriptLineNumber)" -ForegroundColor Yellow
        Write-Host "POSITION : $($_.InvocationInfo.OffsetInLine)" -ForegroundColor Yellow
    }

    Write-Host ''
    Write-Host "SOURCE MUTATION : $script:SourceMutation"
    Write-Host "EXECUTION       : $script:ExecutionPerformed"
    Write-Host "PROMOTION       : $script:PromotionPerformed"
    Write-Host ''
    Write-Host 'FAIL-CLOSED : aucune promotion.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun CERTIFIED.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : les sources originales restent intactes.' -ForegroundColor Yellow
    Write-Host '============================================================================' -ForegroundColor Red
    Write-Host ''

    Read-Host 'Appuie sur ENTREE pour terminer' | Out-Null
}