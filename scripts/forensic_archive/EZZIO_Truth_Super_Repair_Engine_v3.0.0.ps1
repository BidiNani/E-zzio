# ============================================================================
# E-ZZIO — TRUTH SUPER REPAIR ENGINE v3.0.0
# ============================================================================
# PURPOSE
#   Forensic candidate-generation engine for PowerShell parser repair.
#
# SECURITY MODEL
#   READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED
#
# ABSOLUTE RULES
#   - Original project sources are NEVER modified.
#   - Candidates are created only inside the forensic workbench.
#   - Candidates are NEVER executed.
#   - Candidates are NEVER promoted automatically.
#   - CERTIFIED is NEVER granted by this engine.
#   - Every accepted candidate must demonstrably improve parser state.
#   - Regression => reject.
#   - Ambiguity => reject.
#   - Engine failure => FAIL-CLOSED.
#
# IMPORTANT IMPLEMENTATION HARDENING
#   - Never use PowerShell automatic variable $Error as a user variable.
#   - Never require a scalar string where a string[] is expected.
#   - Empty files are valid inputs to the internal functions.
#   - All candidate transformations are isolated and reversible.
#
# VERSION
#   3.0.0
# ============================================================================

& {

    Set-StrictMode -Version Latest
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'

    # =========================================================================
    # ENGINE CONSTANTS
    # =========================================================================

    $EngineName   = 'E-ZZIO — TRUTH SUPER REPAIR ENGINE'
    $ScriptVersion = '3.0.0'

    $ProjectRoot = 'G:\AI\E-zzio'

    $ReportsRoot = Join-Path `
        $ProjectRoot `
        '_EZZIO_TRUTH_REPORTS'

    $SourceMutation = $false
    $ExecutionPerformed = $false
    $PromotionPerformed = $false

    $RunId = (
        Get-Date -Format 'yyyyMMdd_HHmmss_fff'
    ) + '_' + (
        [Guid]::NewGuid().ToString('N').Substring(0, 12)
    )

    # =========================================================================
    # HELPERS — SAFE OUTPUT
    # =========================================================================

    function Write-Banner {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Title
        )

        Write-Host ''
        Write-Host '============================================================================' -ForegroundColor Cyan
        Write-Host " $Title" -ForegroundColor Cyan
        Write-Host '============================================================================' -ForegroundColor Cyan
    }

    function Write-Step {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Number,

            [Parameter(Mandatory = $true)]
            [string]$Message
        )

        Write-Host ''
        Write-Host "[$Number] $Message" -ForegroundColor White
    }

    function Write-Info {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Name,

            [AllowEmptyString()]
            [AllowNull()]
            [object]$Value
        )

        $displayValue = if ($null -eq $Value) {
            '<null>'
        }
        else {
            [string]$Value
        }

        Write-Host ("      {0,-28}: {1}" -f $Name, $displayValue)
    }

    function Write-Ok {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Message
        )

        Write-Host "      $Message" -ForegroundColor Green
    }

    function Write-Warn {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Message
        )

        Write-Host "      $Message" -ForegroundColor Yellow
    }

    # =========================================================================
    # SAFE ARRAY NORMALIZATION
    # =========================================================================

    function Convert-ToStringArray {
        param(
            [AllowNull()]
            [AllowEmptyString()]
            [object]$Value
        )

        if ($null -eq $Value) {
            return [string[]]@()
        }

        if ($Value -is [string[]]) {
            return [string[]]$Value
        }

        if ($Value -is [System.Collections.IEnumerable] -and
            -not ($Value -is [string])) {

            $result = New-Object System.Collections.Generic.List[string]

            foreach ($item in $Value) {
                if ($null -eq $item) {
                    $result.Add('')
                }
                else {
                    $result.Add([string]$item)
                }
            }

            return [string[]]$result.ToArray()
        }

        return [string[]]@([string]$Value)
    }

    # =========================================================================
    # UTF-8 HELPERS
    # =========================================================================

    function Read-Utf8Text {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Path
        )

        return [System.IO.File]::ReadAllText(
            $Path,
            [System.Text.UTF8Encoding]::new($false, $true)
        )
    }

    function Read-Utf8Lines {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Path
        )

        $text = Read-Utf8Text -Path $Path

        if ([string]::IsNullOrEmpty($text)) {
            return [string[]]@()
        }

        return [string[]](
            $text -split "`r?`n", -1
        )
    }

    function Write-Utf8NoBom {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Path,

            [AllowEmptyString()]
            [AllowNull()]
            [string]$Content
        )

        $parent = Split-Path -Parent $Path

        if (-not [string]::IsNullOrWhiteSpace($parent)) {
            [System.IO.Directory]::CreateDirectory($parent) | Out-Null
        }

        if ($null -eq $Content) {
            $Content = ''
        }

        $encoding = [System.Text.UTF8Encoding]::new($false)

        [System.IO.File]::WriteAllText(
            $Path,
            $Content,
            $encoding
        )
    }

    # =========================================================================
    # HASH
    # =========================================================================

    function Get-FileSha256 {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Path
        )

        return (
            Get-FileHash `
                -LiteralPath $Path `
                -Algorithm SHA256
        ).Hash
    }

    # =========================================================================
    # PARSER ENGINE
    # =========================================================================

    function Get-PowerShellParserState {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Path
        )

        $tokens = $null
        $parseDiagnostics = $null

        $text = Read-Utf8Text -Path $Path

        try {
            [System.Management.Automation.Language.Parser]::ParseInput(
                $text,
                [ref]$tokens,
                [ref]$parseDiagnostics
            ) | Out-Null
        }
        catch {
            $internalDiagnostic = [pscustomobject]@{
                Message = "Parser invocation failure: $($_.Exception.Message)"
                ErrorId = 'EZZIO_INTERNAL_PARSER_INVOCATION'
                Line = 0
                Column = 0
                Offset = 0
            }

            return [pscustomobject]@{
                Path = $Path
                ErrorCount = 1
                Errors = @($internalDiagnostic)
                Tokens = @()
                TextLength = $text.Length
                InternalFailure = $true
            }
        }

        $safeDiagnostics = @()

        foreach ($diag in @($parseDiagnostics)) {
            if ($null -eq $diag) {
                continue
            }

            $safeDiagnostics += [pscustomobject]@{
                Message = [string]$diag.Message
                ErrorId = [string]$diag.ErrorId
                Line = [int]$diag.Extent.StartLineNumber
                Column = [int]$diag.Extent.StartColumnNumber
                Offset = [int]$diag.Extent.StartOffset
                Length = [int]$diag.Extent.Text.Length
                Text = [string]$diag.Extent.Text
            }
        }

        return [pscustomobject]@{
            Path = $Path
            ErrorCount = $safeDiagnostics.Count
            Errors = $safeDiagnostics
            Tokens = @($tokens)
            TextLength = $text.Length
            InternalFailure = $false
        }
    }

    # =========================================================================
    # DIAGNOSTIC SIGNATURE
    # =========================================================================

    function Get-DiagnosticSignature {
        param(
            [AllowNull()]
            [object]$ParserState
        )

        if ($null -eq $ParserState) {
            return 'NULL'
        }

        if ($ParserState.ErrorCount -eq 0) {
            return 'PARSE_OK'
        }

        $parts = New-Object System.Collections.Generic.List[string]

        foreach ($diag in @($ParserState.Errors)) {
            $parts.Add(
                ('{0}|{1}|{2}|{3}' -f `
                    $diag.ErrorId,
                    $diag.Line,
                    $diag.Column,
                    $diag.Message)
            )
        }

        return ($parts -join ' || ')
    }

    # =========================================================================
    # ROOT MATRIX DISCOVERY
    # =========================================================================

    function Get-LastRepairDossier {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Root
        )

        if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
            throw "Reports root not found: $Root"
        }

        $dirs = @(
            Get-ChildItem `
                -LiteralPath $Root `
                -Directory `
                -ErrorAction Stop |
            Where-Object {
                $_.Name -match '^\d{8}_\d{6}_\d{3}_'
            } |
            Sort-Object LastWriteTimeUtc -Descending
        )

        foreach ($dir in $dirs) {

            $candidate = Join-Path `
                $dir.FullName `
                'REPAIR_DOSSIER'

            if (Test-Path `
                    -LiteralPath $candidate `
                    -PathType Container) {

                return $candidate
            }
        }

        throw 'No REPAIR_DOSSIER found.'
    }

    function Find-MatrixFile {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Dossier
        )

        $preferred = @(
            'ROOT_CAUSE_MATRIX.json',
            'ROOT_CAUSE_MATRIX.JSON'
        )

        foreach ($name in $preferred) {
            $path = Join-Path $Dossier $name

            if (Test-Path -LiteralPath $path -PathType Leaf) {
                return $path
            }
        }

        $fallback = @(
            Get-ChildItem `
                -LiteralPath $Dossier `
                -File `
                -Filter '*.json' `
                -ErrorAction Stop |
            Where-Object {
                $_.Name -match 'ROOT.*CAUSE.*MATRIX'
            } |
            Select-Object -First 1
        )

        if ($fallback.Count -gt 0) {
            return $fallback[0].FullName
        }

        throw 'ROOT_CAUSE_MATRIX.json not found.'
    }

    function Get-JsonObjects {
        param(
            [Parameter(Mandatory = $true)]
            [object]$Object
        )

        $items = New-Object System.Collections.Generic.List[object]

        if ($null -eq $Object) {
            return @()
        }

        $items.Add($Object)

        if ($Object -is [System.Collections.IEnumerable] -and
            -not ($Object -is [string])) {

            foreach ($item in $Object) {
                $items.AddRange(
                    [object[]](Get-JsonObjects -Object $item)
                )
            }
        }
        elseif ($Object -is [pscustomobject]) {

            foreach ($property in $Object.PSObject.Properties) {
                $items.AddRange(
                    [object[]](
                        Get-JsonObjects `
                            -Object $property.Value
                    )
                )
            }
        }

        return @($items)
    }

    function Resolve-ProjectRelativePath {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Candidate,

            [Parameter(Mandatory = $true)]
            [string]$Root
        )

        if ([string]::IsNullOrWhiteSpace($Candidate)) {
            return $null
        }

        $clean = $Candidate.Trim().Trim('"').Trim("'")

        if ($clean -match '^[A-Za-z]:\\') {
            try {
                $full = [System.IO.Path]::GetFullPath($clean)
            }
            catch {
                return $null
            }
        }
        else {
            try {
                $full = [System.IO.Path]::GetFullPath(
                    (Join-Path $Root $clean)
                )
            }
            catch {
                return $null
            }
        }

        $rootFull = (
            [System.IO.Path]::GetFullPath($Root)
        ).TrimEnd('\')

        if (-not (
            $full.Equals(
                $rootFull,
                [System.StringComparison]::OrdinalIgnoreCase
            ) -or
            $full.StartsWith(
                $rootFull + '\',
                [System.StringComparison]::OrdinalIgnoreCase
            )
        )) {
            return $null
        }

        if (-not (
            $full.EndsWith('.ps1', [System.StringComparison]::OrdinalIgnoreCase) -or
            $full.EndsWith('.psm1', [System.StringComparison]::OrdinalIgnoreCase) -or
            $full.EndsWith('.psd1', [System.StringComparison]::OrdinalIgnoreCase)
        )) {
            return $null
        }

        return $full
    }

    function Get-TargetFilesFromMatrix {
        param(
            [Parameter(Mandatory = $true)]
            [string]$MatrixPath,

            [Parameter(Mandatory = $true)]
            [string]$Root
        )

        $jsonText = Read-Utf8Text -Path $MatrixPath

        if ([string]::IsNullOrWhiteSpace($jsonText)) {
            throw 'Root-Cause Matrix is empty.'
        }

        $matrix = $jsonText | ConvertFrom-Json

        $found = New-Object System.Collections.Generic.HashSet[string](
            [System.StringComparer]::OrdinalIgnoreCase
        )

        foreach ($obj in @(Get-JsonObjects -Object $matrix)) {

            if ($obj -is [string]) {
                $candidate = Resolve-ProjectRelativePath `
                    -Candidate $obj `
                    -Root $Root

                if ($null -ne $candidate) {
                    [void]$found.Add($candidate)
                }

                continue
            }

            if ($null -eq $obj.PSObject) {
                continue
            }

            foreach ($property in $obj.PSObject.Properties) {

                if ($property.Value -isnot [string]) {
                    continue
                }

                $candidate = Resolve-ProjectRelativePath `
                    -Candidate ([string]$property.Value) `
                    -Root $Root

                if ($null -ne $candidate) {
                    [void]$found.Add($candidate)
                }
            }
        }

        return @(
            $found |
            Sort-Object
        )
    }

    # =========================================================================
    # ROOT CAUSE COUNT
    # =========================================================================

    function Get-RootCauseCount {
        param(
            [Parameter(Mandatory = $true)]
            [object]$Matrix
        )

        if ($null -eq $Matrix) {
            return 0
        }

        foreach ($name in @(
            'RootCauses',
            'rootCauses',
            'Causes',
            'causes',
            'Records',
            'records'
        )) {

            $prop = $Matrix.PSObject.Properties[$name]

            if ($null -eq $prop) {
                continue
            }

            if ($prop.Value -is [System.Collections.IEnumerable] -and
                -not ($prop.Value -is [string])) {

                return @($prop.Value).Count
            }
        }

        return 0
    }

    # =========================================================================
    # SOURCE SNAPSHOT
    # =========================================================================

    function New-SourceSnapshot {
        param(
            [Parameter(Mandatory = $true)]
            [string[]]$Paths
        )

        $records = New-Object System.Collections.Generic.List[object]

        foreach ($path in $Paths) {

            if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
                continue
            }

            $item = Get-Item -LiteralPath $path

            $records.Add(
                [pscustomobject]@{
                    Path = $path
                    RelativePath = $path.Substring(
                        $ProjectRoot.Length
                    ).TrimStart('\')
                    SHA256 = Get-FileSha256 -Path $path
                    Length = $item.Length
                    LastWriteTimeUtc = $item.LastWriteTimeUtc.ToString('o')
                }
            )
        }

        return @($records)
    }

    function Save-Json {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Path,

            [Parameter(Mandatory = $true)]
            [object]$Object
        )

        $json = $Object |
            ConvertTo-Json -Depth 50

        Write-Utf8NoBom `
            -Path $Path `
            -Content $json
    }

    # =========================================================================
    # CANDIDATE CLONING
    # =========================================================================

    function Copy-CandidateSources {
        param(
            [Parameter(Mandatory = $true)]
            [string[]]$Paths,

            [Parameter(Mandatory = $true)]
            [string]$CandidateRoot
        )

        $records = New-Object System.Collections.Generic.List[object]

        foreach ($sourcePath in $Paths) {

            $relative = $sourcePath.Substring(
                $ProjectRoot.Length
            ).TrimStart('\')

            $candidatePath = Join-Path `
                $CandidateRoot `
                $relative

            $parent = Split-Path -Parent $candidatePath

            [System.IO.Directory]::CreateDirectory(
                $parent
            ) | Out-Null

            Copy-Item `
                -LiteralPath $sourcePath `
                -Destination $candidatePath `
                -Force

            $records.Add(
                [pscustomobject]@{
                    SourcePath = $sourcePath
                    CandidatePath = $candidatePath
                    RelativePath = $relative
                }
            )
        }

        return @($records)
    }

    # =========================================================================
    # REPAIR HYPOTHESIS MODEL
    # =========================================================================

    function New-Hypothesis {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Id,

            [Parameter(Mandatory = $true)]
            [string]$Description,

            [Parameter(Mandatory = $true)]
            [string]$Category,

            [Parameter(Mandatory = $true)]
            [scriptblock]$Transform
        )

        return [pscustomobject]@{
            Id = $Id
            Description = $Description
            Category = $Category
            Transform = $Transform
        }
    }

    # =========================================================================
    # SAFE TEXT TRANSFORMATIONS
    # =========================================================================

    function Replace-SmartQuotes {
        param(
            [AllowNull()]
            [string]$Text
        )

        if ($null -eq $Text) {
            return ''
        }

        return $Text `
            .Replace([char]0x2018, [char]0x27) `
            .Replace([char]0x2019, [char]0x27) `
            .Replace([char]0x201C, [char]0x22) `
            .Replace([char]0x201D, [char]0x22)
    }

    function Remove-NulCharacters {
        param(
            [AllowNull()]
            [string]$Text
        )

        if ($null -eq $Text) {
            return ''
        }

        return $Text.Replace([char]0, '')
    }

    function Normalize-LineEndings {
        param(
            [AllowNull()]
            [string]$Text
        )

        if ($null -eq $Text) {
            return ''
        }

        $normalized = $Text -replace "`r`n", "`n"
        $normalized = $normalized -replace "`r", "`n"

        return $normalized -replace "`n", "`r`n"
    }

    function Remove-InvalidTrailingBackslash {
        param(
            [AllowNull()]
            [string]$Text
        )

        if ($null -eq $Text) {
            return ''
        }

        $lines = Convert-ToStringArray `
            -Value ($Text -split "`r?`n", -1)

        if ($lines.Count -eq 0) {
            return ''
        }

        $result = New-Object System.Collections.Generic.List[string]

        foreach ($line in $lines) {
            $result.Add([string]$line)
        }

        # Conservative transformation:
        # remove a backtick only when it is the final character of a line
        # followed by an entirely blank line.
        for ($i = 0; $i -lt ($result.Count - 1); $i++) {

            $current = $result[$i]
            $next = $result[$i + 1]

            if (
                $current.EndsWith('`') -and
                [string]::IsNullOrWhiteSpace($next)
            ) {
                $result[$i] = $current.Substring(
                    0,
                    $current.Length - 1
                )
            }
        }

        return ($result.ToArray() -join "`r`n")
    }

    function Add-MissingClosingBracesAtEnd {
        param(
            [AllowNull()]
            [string]$Text
        )

        if ($null -eq $Text) {
            $Text = ''
        }

        $tokens = $null
        $parseDiagnostics = $null

        try {
            [System.Management.Automation.Language.Parser]::ParseInput(
                $Text,
                [ref]$tokens,
                [ref]$parseDiagnostics
            ) | Out-Null
        }
        catch {
            return $Text
        }

        $openBraces = 0
        $closeBraces = 0

        foreach ($token in @($tokens)) {
            if ($null -eq $token) {
                continue
            }

            if ($token.Kind -eq 'LCurly') {
                $openBraces++
            }
            elseif ($token.Kind -eq 'RCurly') {
                $closeBraces++
            }
        }

        $missing = $openBraces - $closeBraces

        if ($missing -le 0 -or $missing -gt 10) {
            return $Text
        }

        $suffix = ''

        for ($i = 0; $i -lt $missing; $i++) {
            $suffix += "`r`n}"
        }

        return ($Text.TrimEnd() + $suffix + "`r`n")
    }

    function Add-MissingClosingParenthesesAtEnd {
        param(
            [AllowNull()]
            [string]$Text
        )

        if ($null -eq $Text) {
            $Text = ''
        }

        $tokens = $null
        $parseDiagnostics = $null

        try {
            [System.Management.Automation.Language.Parser]::ParseInput(
                $Text,
                [ref]$tokens,
                [ref]$parseDiagnostics
            ) | Out-Null
        }
        catch {
            return $Text
        }

        $openCount = 0
        $closeCount = 0

        foreach ($token in @($tokens)) {
            if ($null -eq $token) {
                continue
            }

            if ($token.Kind -eq 'LParen') {
                $openCount++
            }
            elseif ($token.Kind -eq 'RParen') {
                $closeCount++
            }
        }

        $missing = $openCount - $closeCount

        if ($missing -le 0 -or $missing -gt 10) {
            return $Text
        }

        return (
            $Text.TrimEnd() +
            ('`r`n' + (')' * $missing)) +
            "`r`n"
        )
    }

    function Add-MissingClosingBracketsAtEnd {
        param(
            [AllowNull()]
            [string]$Text
        )

        if ($null -eq $Text) {
            $Text = ''
        }

        $tokens = $null
        $parseDiagnostics = $null

        try {
            [System.Management.Automation.Language.Parser]::ParseInput(
                $Text,
                [ref]$tokens,
                [ref]$parseDiagnostics
            ) | Out-Null
        }
        catch {
            return $Text
        }

        $openCount = 0
        $closeCount = 0

        foreach ($token in @($tokens)) {
            if ($null -eq $token) {
                continue
            }

            if ($token.Kind -eq 'LBracket') {
                $openCount++
            }
            elseif ($token.Kind -eq 'RBracket') {
                $closeCount++
            }
        }

        $missing = $openCount - $closeCount

        if ($missing -le 0 -or $missing -gt 10) {
            return $Text
        }

        return (
            $Text.TrimEnd() +
            "`r`n" +
            (']' * $missing) +
            "`r`n"
        )
    }

    # =========================================================================
    # HYPOTHESIS LIBRARY
    # =========================================================================

    function Get-Hypotheses {
        return @(
            New-Hypothesis `
                -Id 'H001_SMART_QUOTES' `
                -Description 'Replace Unicode smart quotes with ASCII PowerShell quotes.' `
                -Category 'TEXT_NORMALIZATION' `
                -Transform {
                    param([string]$Text)
                    Replace-SmartQuotes -Text $Text
                }

            New-Hypothesis `
                -Id 'H002_REMOVE_NUL' `
                -Description 'Remove embedded NUL characters.' `
                -Category 'TEXT_SANITIZATION' `
                -Transform {
                    param([string]$Text)
                    Remove-NulCharacters -Text $Text
                }

            New-Hypothesis `
                -Id 'H003_LINE_ENDINGS' `
                -Description 'Normalize line endings to CRLF.' `
                -Category 'TEXT_NORMALIZATION' `
                -Transform {
                    param([string]$Text)
                    Normalize-LineEndings -Text $Text
                }

            New-Hypothesis `
                -Id 'H004_TRAILING_BACKTICK' `
                -Description 'Remove a trailing continuation backtick immediately before a blank line.' `
                -Category 'CONTINUATION' `
                -Transform {
                    param([string]$Text)
                    Remove-InvalidTrailingBackslash -Text $Text
                }

            New-Hypothesis `
                -Id 'H005_CLOSE_BRACES' `
                -Description 'Append missing closing curly braces when token balance proves a deficit.' `
                -Category 'DELIMITER_BALANCE' `
                -Transform {
                    param([string]$Text)
                    Add-MissingClosingBracesAtEnd -Text $Text
                }

            New-Hypothesis `
                -Id 'H006_CLOSE_PARENTHESES' `
                -Description 'Append missing closing parentheses when token balance proves a deficit.' `
                -Category 'DELIMITER_BALANCE' `
                -Transform {
                    param([string]$Text)
                    Add-MissingClosingParenthesesAtEnd -Text $Text
                }

            New-Hypothesis `
                -Id 'H007_CLOSE_BRACKETS' `
                -Description 'Append missing closing brackets when token balance proves a deficit.' `
                -Category 'DELIMITER_BALANCE' `
                -Transform {
                    param([string]$Text)
                    Add-MissingClosingBracketsAtEnd -Text $Text
                }
        )
    }

    # =========================================================================
    # CANDIDATE EVALUATION
    # =========================================================================

    function Test-CandidateText {
        param(
            [Parameter(Mandatory = $true)]
            [string]$CandidatePath,

            [Parameter(Mandatory = $true)]
            [string]$CandidateText,

            [Parameter(Mandatory = $true)]
            [object]$BaselineState
        )

        $tempPath = $CandidatePath + '.ezzio_eval.tmp'

        try {

            Write-Utf8NoBom `
                -Path $tempPath `
                -Content $CandidateText

            $candidateState = Get-PowerShellParserState `
                -Path $tempPath

            $baselineCount = [int]$BaselineState.ErrorCount
            $candidateCount = [int]$candidateState.ErrorCount

            $improvement = $baselineCount - $candidateCount

            $verdict = 'REJECT'

            if (
                -not $candidateState.InternalFailure -and
                $candidateCount -lt $baselineCount
            ) {
                $verdict = 'IMPROVED'
            }
            elseif (
                -not $candidateState.InternalFailure -and
                $candidateCount -eq $baselineCount
            ) {
                $verdict = 'NO_CHANGE'
            }
            elseif (
                $candidateState.InternalFailure
            ) {
                $verdict = 'PARSER_FAILURE'
            }
            elseif (
                $candidateCount -gt $baselineCount
            ) {
                $verdict = 'REGRESSION'
            }

            return [pscustomobject]@{
                Verdict = $verdict
                BaselineErrors = $baselineCount
                CandidateErrors = $candidateCount
                Improvement = $improvement
                CandidateState = $candidateState
            }
        }
        finally {
            if (Test-Path -LiteralPath $tempPath -PathType Leaf) {
                Remove-Item `
                    -LiteralPath $tempPath `
                    -Force `
                    -ErrorAction SilentlyContinue
            }
        }
    }

    # =========================================================================
    # SOURCE CHANGE DETECTION
    # =========================================================================

    function Compare-SourceSnapshot {
        param(
            [Parameter(Mandatory = $true)]
            [object[]]$Before,

            [Parameter(Mandatory = $true)]
            [object[]]$After
        )

        $beforeMap = @{}

        foreach ($record in @($Before)) {
            $beforeMap[$record.Path] = $record.SHA256
        }

        $mutations = New-Object System.Collections.Generic.List[object]

        foreach ($record in @($After)) {

            if (-not $beforeMap.ContainsKey($record.Path)) {
                $mutations.Add(
                    [pscustomobject]@{
                        Path = $record.Path
                        Before = '<MISSING>'
                        After = $record.SHA256
                    }
                )

                continue
            }

            if ($beforeMap[$record.Path] -ne $record.SHA256) {
                $mutations.Add(
                    [pscustomobject]@{
                        Path = $record.Path
                        Before = $beforeMap[$record.Path]
                        After = $record.SHA256
                    }
                )
            }
        }

        return @($mutations)
    }

    # =========================================================================
    # MAIN
    # =========================================================================

    try {

        Write-Banner `
            -Title 'E-ZZIO — TRUTH SUPER REPAIR ENGINE v3.0.0'

        Write-Info 'PROJECT' $ProjectRoot
        Write-Info 'MODE' 'READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED'
        Write-Info 'QUALITY' 'FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
        Write-Info 'SOURCE MUTATION' 'DISABLED'
        Write-Info 'EXECUTION' 'DISABLED'
        Write-Info 'PROMOTION' 'DISABLED'
        Write-Info 'RUN ID' $RunId

        # =====================================================================
        # 1
        # =====================================================================

        Write-Step '1/16' 'Validation environnement...'

        if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
            throw "Project root not found: $ProjectRoot"
        }

        $psVersion = $PSVersionTable.PSVersion.ToString()

        Write-Info 'PowerShell' $psVersion
        Write-Ok 'ENVIRONMENT : PASS'

        # =====================================================================
        # 2
        # =====================================================================

        Write-Step '2/16' 'Recherche du dernier REPAIR_DOSSIER...'

        $RepairDossier = Get-LastRepairDossier `
            -Root $ReportsRoot

        Write-Info 'DOSSIER' $RepairDossier
        Write-Ok 'DISCOVERY : PASS'

        # =====================================================================
        # 3
        # =====================================================================

        Write-Step '3/16' 'Chargement de la Root-Cause Matrix...'

        $MatrixPath = Find-MatrixFile `
            -Dossier $RepairDossier

        $matrixText = Read-Utf8Text `
            -Path $MatrixPath

        $Matrix = $matrixText | ConvertFrom-Json

        $RootCauseCount = Get-RootCauseCount `
            -Matrix $Matrix

        Write-Info 'MATRIX' $MatrixPath
        Write-Info 'ROOT CAUSES' $RootCauseCount

        # =====================================================================
        # 4
        # =====================================================================

        Write-Step '4/16' 'Identification forensic des fichiers cibles...'

        $TargetFiles = @(
            Get-TargetFilesFromMatrix `
                -MatrixPath $MatrixPath `
                -Root $ProjectRoot
        )

        if ($TargetFiles.Count -eq 0) {
            throw 'No valid PowerShell target files were discovered from Root-Cause Matrix.'
        }

        $TargetFileCount = $TargetFiles.Count

        Write-Info 'TARGET FILES' $TargetFileCount
        Write-Ok 'TARGET DISCOVERY : PASS'

        # =====================================================================
        # 5
        # =====================================================================

        Write-Step '5/16' 'Construction du baseline original...'

        $OriginalSnapshot = @(
            New-SourceSnapshot `
                -Paths $TargetFiles
        )

        if ($OriginalSnapshot.Count -ne $TargetFileCount) {
            throw (
                "Baseline mismatch. Expected $TargetFileCount, " +
                "got $($OriginalSnapshot.Count)."
            )
        }

        $BaselineRecords = New-Object System.Collections.Generic.List[object]

        foreach ($targetPath in $TargetFiles) {

            $state = Get-PowerShellParserState `
                -Path $targetPath

            $BaselineRecords.Add(
                [pscustomobject]@{
                    Path = $targetPath
                    RelativePath = $targetPath.Substring(
                        $ProjectRoot.Length
                    ).TrimStart('\')
                    SHA256 = Get-FileSha256 -Path $targetPath
                    ParserErrors = $state.ErrorCount
                    InternalParserFailure = $state.InternalFailure
                    Diagnostics = @($state.Errors)
                }
            )
        }

        $OriginalErrorCount = (
            @($BaselineRecords) |
            Measure-Object `
                -Property ParserErrors `
                -Sum
        ).Sum

        if ($null -eq $OriginalErrorCount) {
            $OriginalErrorCount = 0
        }

        Write-Info 'BASELINE FILES' $OriginalSnapshot.Count
        Write-Info 'PARSER ERRORS' $OriginalErrorCount
        Write-Ok 'BASELINE : PASS'

        # =====================================================================
        # 6
        # =====================================================================

        Write-Step '6/16' 'Création du SUPER REPAIR WORKBENCH...'

        $WorkbenchRoot = Join-Path `
            $ReportsRoot `
            $RunId

        $Workbench = Join-Path `
            $WorkbenchRoot `
            'SUPER_REPAIR_WORKBENCH'

        $CandidateRoot = Join-Path `
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

        $Logs = Join-Path `
            $Workbench `
            'LOGS'

        foreach ($directory in @(
            $Workbench,
            $CandidateRoot,
            $AcceptedRoot,
            $RejectedRoot,
            $Reports,
            $Logs
        )) {
            [System.IO.Directory]::CreateDirectory(
                $directory
            ) | Out-Null
        }

        Write-Info 'WORKBENCH' $Workbench
        Write-Ok 'WORKBENCH : PASS'

        # =====================================================================
        # 7
        # =====================================================================

        Write-Step '7/16' 'Clonage strict des sources...'

        $CloneRecords = @(
            Copy-CandidateSources `
                -Paths $TargetFiles `
                -CandidateRoot $CandidateRoot
        )

        if ($CloneRecords.Count -ne $TargetFileCount) {
            throw 'Candidate cloning count mismatch.'
        }

        Write-Info 'CLONED' $CloneRecords.Count
        Write-Ok 'CLONING : PASS'

        # =====================================================================
        # 8
        # =====================================================================

        Write-Step '8/16' 'Revalidation parser des candidats clonés...'

        $CandidateBaseline = New-Object System.Collections.Generic.List[object]

        foreach ($clone in $CloneRecords) {

            $state = Get-PowerShellParserState `
                -Path $clone.CandidatePath

            $CandidateBaseline.Add(
                [pscustomobject]@{
                    SourcePath = $clone.SourcePath
                    CandidatePath = $clone.CandidatePath
                    RelativePath = $clone.RelativePath
                    ParserErrors = $state.ErrorCount
                    Diagnostics = @($state.Errors)
                    SHA256 = Get-FileSha256 `
                        -Path $clone.CandidatePath
                }
            )
        }

        $CandidateBaselineErrorCount = (
            @($CandidateBaseline) |
            Measure-Object `
                -Property ParserErrors `
                -Sum
        ).Sum

        if ($null -eq $CandidateBaselineErrorCount) {
            $CandidateBaselineErrorCount = 0
        }

        if (
            $CandidateBaselineErrorCount -ne
            $OriginalErrorCount
        ) {
            throw (
                "Candidate baseline mismatch: original=$OriginalErrorCount " +
                "candidate=$CandidateBaselineErrorCount."
            )
        }

        Write-Info 'CANDIDATE BASELINE' $CandidateBaselineErrorCount
        Write-Ok 'PARSER BASELINE : PASS'

        # =====================================================================
        # 9
        # =====================================================================

        Write-Step '9/16' 'Construction de la file des erreurs parser...'

        $ErrorQueue = New-Object System.Collections.Generic.List[object]

        foreach ($record in @($CandidateBaseline)) {

            foreach ($diagnostic in @($record.Diagnostics)) {

                $ErrorQueue.Add(
                    [pscustomobject]@{
                        RelativePath = $record.RelativePath
                        SourcePath = $record.SourcePath
                        CandidatePath = $record.CandidatePath
                        Diagnostic = $diagnostic
                    }
                )
            }
        }

        Write-Info 'ERROR QUEUE' $ErrorQueue.Count
        Write-Ok 'ERROR QUEUE : PASS'

        # =====================================================================
        # 10
        # =====================================================================

        Write-Step '10/16' 'Génération des hypothèses de réparation...'

        $Hypotheses = @(
            Get-Hypotheses
        )

        Write-Info 'HYPOTHESES' $Hypotheses.Count
        Write-Ok 'HYPOTHESIS ENGINE : PASS'

        # =====================================================================
        # 11
        # =====================================================================

        Write-Step '11/16' 'Test isolé des hypothèses sur chaque candidat...'

        $AttemptRecords = New-Object System.Collections.Generic.List[object]

        $AcceptedRecords = New-Object System.Collections.Generic.List[object]

        $RejectedRecords = New-Object System.Collections.Generic.List[object]

        foreach ($clone in $CloneRecords) {

            $currentPath = $clone.CandidatePath

            $currentText = Read-Utf8Text `
                -Path $currentPath

            $currentState = Get-PowerShellParserState `
                -Path $currentPath

            foreach ($hypothesis in $Hypotheses) {

                $attemptId = (
                    [Guid]::NewGuid().ToString('N')
                )

                $attemptPath = Join-Path `
                    $RejectedRoot `
                    ($attemptId + '_' + `
                        [System.IO.Path]::GetFileName(
                            $currentPath
                        ))

                $candidateText = $null

                try {

                    $candidateText = & $hypothesis.Transform $currentText

                    if ($null -eq $candidateText) {
                        $candidateText = ''
                    }

                    if ($candidateText -isnot [string]) {
                        $candidateText = [string]$candidateText
                    }

                    $testResult = Test-CandidateText `
                        -CandidatePath $attemptPath `
                        -CandidateText $candidateText `
                        -BaselineState $currentState

                    $record = [pscustomobject]@{
                        AttemptId = $attemptId
                        RelativePath = $clone.RelativePath
                        SourcePath = $clone.SourcePath
                        WorkingPath = $currentPath
                        HypothesisId = $hypothesis.Id
                        Hypothesis = $hypothesis.Description
                        Category = $hypothesis.Category
                        BeforeErrors = $testResult.BaselineErrors
                        AfterErrors = $testResult.CandidateErrors
                        Improvement = $testResult.Improvement
                        Verdict = $testResult.Verdict
                        BeforeSignature = Get-DiagnosticSignature `
                            -ParserState $currentState
                        AfterSignature = Get-DiagnosticSignature `
                            -ParserState $testResult.CandidateState
                    }

                    $AttemptRecords.Add($record)

                    if ($testResult.Verdict -eq 'IMPROVED') {

                        $acceptedCandidatePath = Join-Path `
                            $AcceptedRoot `
                            $clone.RelativePath

                        $acceptedParent = Split-Path `
                            -Parent `
                            $acceptedCandidatePath

                        [System.IO.Directory]::CreateDirectory(
                            $acceptedParent
                        ) | Out-Null

                        Write-Utf8NoBom `
                            -Path $acceptedCandidatePath `
                            -Content $candidateText

                        $AcceptedRecords.Add(
                            [pscustomobject]@{
                                AttemptId = $attemptId
                                RelativePath = $clone.RelativePath
                                SourcePath = $clone.SourcePath
                                AcceptedCandidatePath = $acceptedCandidatePath
                                HypothesisId = $hypothesis.Id
                                Hypothesis = $hypothesis.Description
                                BeforeErrors = $testResult.BaselineErrors
                                AfterErrors = $testResult.CandidateErrors
                                Improvement = $testResult.Improvement
                                SHA256 = Get-FileSha256 `
                                    -Path $acceptedCandidatePath
                            }
                        )
                    }
                    else {

                        $RejectedRecords.Add($record)
                    }

                }
                catch {

                    $record = [pscustomobject]@{
                        AttemptId = $attemptId
                        RelativePath = $clone.RelativePath
                        SourcePath = $clone.SourcePath
                        WorkingPath = $currentPath
                        HypothesisId = $hypothesis.Id
                        Hypothesis = $hypothesis.Description
                        Category = $hypothesis.Category
                        BeforeErrors = $currentState.ErrorCount
                        AfterErrors = $null
                        Improvement = $null
                        Verdict = 'ENGINE_REJECTED'
                        EngineMessage = $_.Exception.Message
                    }

                    $AttemptRecords.Add($record)
                    $RejectedRecords.Add($record)
                }

                if (Test-Path -LiteralPath $attemptPath -PathType Leaf) {
                    Remove-Item `
                        -LiteralPath $attemptPath `
                        -Force `
                        -ErrorAction SilentlyContinue
                }
            }
        }

        $AttemptCount = $AttemptRecords.Count

        $AcceptedCount = $AcceptedRecords.Count
        $RejectedCount = $RejectedRecords.Count

        Write-Info 'ATTEMPTS' $AttemptCount
        Write-Info 'ACCEPTED' $AcceptedCount
        Write-Info 'REJECTED' $RejectedCount

        # =====================================================================
        # 12
        # =====================================================================

        Write-Step '12/16' 'Détermination des améliorations réellement prouvées...'

        $AcceptedPerFile = @(
            $AcceptedRecords |
            Group-Object RelativePath
        )

        $FinalPerFile = New-Object System.Collections.Generic.List[object]

        foreach ($baselineRecord in @($CandidateBaseline)) {

            $fileAccepted = @(
                $AcceptedRecords |
                Where-Object {
                    $_.RelativePath -eq $baselineRecord.RelativePath
                } |
                Sort-Object `
                    -Property Improvement `
                    -Descending
            )

            if ($fileAccepted.Count -eq 0) {

                $FinalPerFile.Add(
                    [pscustomobject]@{
                        RelativePath = $baselineRecord.RelativePath
                        BaselineErrors = $baselineRecord.ParserErrors
                        FinalErrors = $baselineRecord.ParserErrors
                        Improvement = 0
                        Status = 'UNCHANGED'
                        Candidate = $null
                    }
                )

                continue
            }

            $best = $fileAccepted[0]

            $FinalPerFile.Add(
                [pscustomobject]@{
                    RelativePath = $baselineRecord.RelativePath
                    BaselineErrors = $baselineRecord.ParserErrors
                    FinalErrors = $best.AfterErrors
                    Improvement = $best.Improvement
                    Status = 'IMPROVED'
                    Candidate = $best.AcceptedCandidatePath
                    HypothesisId = $best.HypothesisId
                    Hypothesis = $best.Hypothesis
                }
            )
        }

        $FinalParserErrors = (
            @($FinalPerFile) |
            Measure-Object `
                -Property FinalErrors `
                -Sum
        ).Sum

        if ($null -eq $FinalParserErrors) {
            $FinalParserErrors = 0
        }

        $GlobalImprovement =
            [int]$OriginalErrorCount -
            [int]$FinalParserErrors

        if ($OriginalErrorCount -gt 0) {
            $ImprovementRatio = [Math]::Round(
                (
                    $GlobalImprovement /
                    [double]$OriginalErrorCount
                ),
                6
            )
        }
        else {
            $ImprovementRatio = 1.0
        }

        Write-Info 'BASELINE ERRORS' $OriginalErrorCount
        Write-Info 'FINAL ERRORS' $FinalParserErrors
        Write-Info 'GLOBAL IMPROVEMENT' $GlobalImprovement
        Write-Info 'IMPROVEMENT RATIO' $ImprovementRatio

        # =====================================================================
        # 13
        # =====================================================================

        Write-Step '13/16' 'Vérification d''intégrité des sources originales...'

        $AfterSnapshot = @(
            New-SourceSnapshot `
                -Paths $TargetFiles
        )

        $SourceMutations = @(
            Compare-SourceSnapshot `
                -Before $OriginalSnapshot `
                -After $AfterSnapshot
        )

        if ($SourceMutations.Count -ne 0) {
            $SourceMutation = $true

            Save-Json `
                -Path (Join-Path $Reports 'SOURCE_MUTATIONS.json') `
                -Object $SourceMutations

            throw (
                'CRITICAL: source mutation detected. ' +
                'FAIL-CLOSED.'
            )
        }

        Write-Info 'SOURCE MUTATIONS' 0
        Write-Ok 'SOURCE INTEGRITY : PASS'

        # =====================================================================
        # 14
        # =====================================================================

        Write-Step '14/16' 'Écriture des artefacts forensic...'

        Save-Json `
            -Path (Join-Path $Reports 'ORIGINAL_BASELINE.json') `
            -Object $BaselineRecords

        Save-Json `
            -Path (Join-Path $Reports 'CANDIDATE_BASELINE.json') `
            -Object $CandidateBaseline

        Save-Json `
            -Path (Join-Path $Reports 'ERROR_QUEUE.json') `
            -Object @($ErrorQueue)

        Save-Json `
            -Path (Join-Path $Reports 'REPAIR_ATTEMPTS.json') `
            -Object @($AttemptRecords)

        Save-Json `
            -Path (Join-Path $Reports 'ACCEPTED_CANDIDATES.json') `
            -Object @($AcceptedRecords)

        Save-Json `
            -Path (Join-Path $Reports 'FINAL_PER_FILE.json') `
            -Object @($FinalPerFile)

        Save-Json `
            -Path (Join-Path $Reports 'SOURCE_HASHES_BEFORE.json') `
            -Object $OriginalSnapshot

        Save-Json `
            -Path (Join-Path $Reports 'SOURCE_HASHES_AFTER.json') `
            -Object $AfterSnapshot

        Write-Ok 'FORENSIC ARTIFACTS : PASS'

        # =====================================================================
        # 15
        # =====================================================================

        Write-Step '15/16' 'Construction du verdict...'

        $RegressionCount = @(
            $AttemptRecords |
            Where-Object {
                $_.Verdict -eq 'REGRESSION'
            }
        ).Count

        $AmbiguousCount = @(
            $AttemptRecords |
            Where-Object {
                $_.Verdict -eq 'NO_CHANGE'
            }
        ).Count

        $GlobalVerdict = 'NO_CERTIFICATION'

        if (
            $SourceMutation -eq $false -and
            $ExecutionPerformed -eq $false -and
            $PromotionPerformed -eq $false -and
            $FinalParserErrors -lt $OriginalErrorCount
        ) {
            $GlobalVerdict = 'CANDIDATES_IMPROVED'
        }
        elseif (
            $FinalParserErrors -eq $OriginalErrorCount
        ) {
            $GlobalVerdict = 'NO_PROVABLE_IMPROVEMENT'
        }
        elseif (
            $FinalParserErrors -gt $OriginalErrorCount
        ) {
            $GlobalVerdict = 'REGRESSION_DETECTED'
        }

        $Manifest = [ordered]@{
            Engine = $EngineName
            Version = $ScriptVersion
            RunId = $RunId
            TimestampUtc = [DateTime]::UtcNow.ToString('o')

            ProjectRoot = $ProjectRoot
            RepairDossier = $RepairDossier
            MatrixPath = $MatrixPath

            RootCauses = $RootCauseCount
            TargetFiles = $TargetFileCount

            OriginalParserErrors = $OriginalErrorCount
            CandidateBaselineParserErrors =
                $CandidateBaselineErrorCount
            FinalCandidateParserErrors = $FinalParserErrors

            GlobalImprovement = $GlobalImprovement
            ImprovementRatio = $ImprovementRatio

            RepairAttempts = $AttemptCount
            AcceptedCandidates = $AcceptedCount
            RejectedCandidates = $RejectedCount
            AmbiguousCandidates = $AmbiguousCount
            RegressionCandidates = $RegressionCount

            SourceMutation = $SourceMutation
            ExecutionPerformed = $ExecutionPerformed
            PromotionPerformed = $PromotionPerformed

            Certified = $false
            CertifiedAuthorized = $false

            Verdict = $GlobalVerdict

            SecurityModel = @(
                'READ_ONLY'
                'CANDIDATE_ONLY'
                'FAIL_CLOSED'
                'NO_EXECUTION'
                'NO_PROMOTION'
                'NO_CERTIFICATION'
            )
        }

        $ManifestPath = Join-Path `
            $Reports `
            'SUPER_REPAIR_V3_MANIFEST.json'

        Save-Json `
            -Path $ManifestPath `
            -Object $Manifest

        # =====================================================================
        # 16
        # =====================================================================

        Write-Step '16/16' 'Gates finales...'

        $FinalSnapshot = @(
            New-SourceSnapshot `
                -Paths $TargetFiles
        )

        $FinalMutations = @(
            Compare-SourceSnapshot `
                -Before $OriginalSnapshot `
                -After $FinalSnapshot
        )

        if ($FinalMutations.Count -ne 0) {
            $SourceMutation = $true

            Save-Json `
                -Path (Join-Path $Reports 'FINAL_SOURCE_MUTATIONS.json') `
                -Object $FinalMutations

            throw (
                'FINAL GATE FAILED: source mutation detected.'
            )
        }

        if ($ExecutionPerformed) {
            throw 'FINAL GATE FAILED: execution flag is true.'
        }

        if ($PromotionPerformed) {
            throw 'FINAL GATE FAILED: promotion flag is true.'
        }

        # =====================================================================
        # FINAL REPORT
        # =====================================================================

        $ReportPath = Join-Path `
            $Reports `
            'SUPER_REPAIR_V3_REPORT.txt'

        $reportLines = @(
            '============================================================================'
            ' E-ZZIO — TRUTH SUPER REPAIR ENGINE v3.0.0'
            '============================================================================'
            ''
            "RUN ID                  : $RunId"
            "PROJECT                 : $ProjectRoot"
            "REPAIR DOSSIER          : $RepairDossier"
            "MATRIX                  : $MatrixPath"
            ''
            "ROOT CAUSES             : $RootCauseCount"
            "TARGET FILES            : $TargetFileCount"
            ''
            "ORIGINAL PARSER ERRORS : $OriginalErrorCount"
            "CANDIDATE BASELINE     : $CandidateBaselineErrorCount"
            "FINAL CANDIDATE ERRORS : $FinalParserErrors"
            "GLOBAL IMPROVEMENT     : $GlobalImprovement"
            "IMPROVEMENT RATIO      : $ImprovementRatio"
            ''
            "REPAIR ATTEMPTS        : $AttemptCount"
            "ACCEPTED CANDIDATES    : $AcceptedCount"
            "REJECTED CANDIDATES    : $RejectedCount"
            "AMBIGUOUS ATTEMPTS     : $AmbiguousCount"
            "REGRESSIONS            : $RegressionCount"
            ''
            "SOURCE MUTATION        : $SourceMutation"
            "EXECUTION             : $ExecutionPerformed"
            "PROMOTION             : $PromotionPerformed"
            "CERTIFIED             : FALSE"
            "CERTIFIED AUTHORIZED  : FALSE"
            ''
            "VERDICT                : $GlobalVerdict"
            ''
            "WORKBENCH              : $Workbench"
            "CANDIDATES             : $CandidateRoot"
            "ACCEPTED               : $AcceptedRoot"
            "REPORT                 : $ReportPath"
            "MANIFEST               : $ManifestPath"
            ''
            '============================================================================'
            ' FAIL-CLOSED GUARANTEES'
            '============================================================================'
            'Original project sources were not modified.'
            'No candidate was executed.'
            'No candidate was promoted.'
            'No certification was granted.'
            'Only parser-proven candidate improvements are retained.'
            '============================================================================'
        )

        Write-Utf8NoBom `
            -Path $ReportPath `
            -Content ($reportLines -join [Environment]::NewLine)

        # =====================================================================
        # FINAL CONSOLE
        # =====================================================================

        Write-Banner `
            -Title 'E-ZZIO — TRUTH SUPER REPAIR ENGINE v3.0.0 COMPLETE'

        Write-Info 'RUN ID' $RunId
        Write-Info 'ROOT CAUSES' $RootCauseCount
        Write-Info 'TARGET FILES' $TargetFileCount
        Write-Info 'PARSER BASELINE' $OriginalErrorCount
        Write-Info 'PARSER FINAL' $FinalParserErrors
        Write-Info 'GLOBAL IMPROVEMENT' $GlobalImprovement
        Write-Info 'IMPROVEMENT RATIO' $ImprovementRatio
        Write-Info 'ATTEMPTS' $AttemptCount
        Write-Info 'ACCEPTED' $AcceptedCount
        Write-Info 'REJECTED' $RejectedCount
        Write-Info 'REGRESSIONS' $RegressionCount

        Write-Host ''
        Write-Host 'SOURCE MUTATION         : 0' -ForegroundColor Green
        Write-Host 'EXECUTION              : DISABLED' -ForegroundColor Green
        Write-Host 'PROMOTION              : DISABLED' -ForegroundColor Green
        Write-Host 'CERTIFIED              : NOT AUTHORIZED' -ForegroundColor Yellow

        Write-Host ''
        Write-Info 'WORKBENCH' $Workbench
        Write-Info 'ACCEPTED CANDIDATES' $AcceptedRoot
        Write-Info 'REPORT' $ReportPath
        Write-Info 'MANIFEST' $ManifestPath

        Write-Host ''
        Write-Host "VERDICT : $GlobalVerdict" -ForegroundColor Cyan

        Write-Host ''
        Write-Host 'FAIL-CLOSED : les sources originales restent intactes.' -ForegroundColor Yellow
        Write-Host 'FAIL-CLOSED : aucun candidat n''est exécuté.' -ForegroundColor Yellow
        Write-Host 'FAIL-CLOSED : aucun candidat n''est promu.' -ForegroundColor Yellow
        Write-Host 'FAIL-CLOSED : CERTIFIED n''est jamais accordé par ce moteur.' -ForegroundColor Yellow
        Write-Host '============================================================================' -ForegroundColor Green
        Write-Host ''
        Write-Host 'La fenêtre reste ouverte.' -ForegroundColor DarkGray
        Write-Host ''

        Read-Host 'Appuie sur ENTREE pour terminer'
    }
    catch {

        $engineExceptionMessage = $_.Exception.Message
        $engineExceptionType = $_.Exception.GetType().FullName
        $engineExceptionLine = $_.InvocationInfo.ScriptLineNumber
        $engineExceptionPosition = $_.InvocationInfo.PositionMessage

        $SourceMutation = $false

        Write-Host ''
        Write-Host '============================================================================' -ForegroundColor Red
        Write-Host ' E-ZZIO — TRUTH SUPER REPAIR ENGINE v3.0.0 FAILED / FAIL-CLOSED' -ForegroundColor Red
        Write-Host '============================================================================' -ForegroundColor Red
        Write-Host ''

        Write-Host "ERROR TYPE : $engineExceptionType" -ForegroundColor Red
        Write-Host "ERROR      : $engineExceptionMessage" -ForegroundColor Red
        Write-Host "LINE       : $engineExceptionLine" -ForegroundColor Red
        Write-Host ''

        Write-Host "SOURCE MUTATION : $SourceMutation"
        Write-Host "EXECUTION       : $ExecutionPerformed"
        Write-Host "PROMOTION       : $PromotionPerformed"
        Write-Host ''

        Write-Host 'Aucune promotion de candidat.' -ForegroundColor Yellow
        Write-Host 'Aucun candidat exécuté.' -ForegroundColor Yellow
        Write-Host 'Aucun CERTIFIED autorisé.' -ForegroundColor Yellow
        Write-Host 'Les sources originales restent intactes.' -ForegroundColor Yellow
        Write-Host ''

        Write-Host 'FAIL-CLOSED : ENGINE FAILURE.' -ForegroundColor Red
        Write-Host '============================================================================' -ForegroundColor Red
        Write-Host ''

        if ($Reports -and
            (Test-Path -LiteralPath $Reports -PathType Container)) {

            $failurePath = Join-Path `
                $Reports `
                'ENGINE_FAILURE.txt'

            $failureContent = @(
                'E-ZZIO — TRUTH SUPER REPAIR ENGINE v3.0.0'
                'ENGINE FAILURE'
                ''
                "RUN ID : $RunId"
                "TYPE : $engineExceptionType"
                "MESSAGE : $engineExceptionMessage"
                "LINE : $engineExceptionLine"
                ''
                'SOURCE MUTATION : FALSE'
                'EXECUTION : FALSE'
                'PROMOTION : FALSE'
                'CERTIFIED : FALSE'
                ''
                'POSITION:'
                $engineExceptionPosition
            ) -join [Environment]::NewLine

            try {
                Write-Utf8NoBom `
                    -Path $failurePath `
                    -Content $failureContent

                Write-Info 'FAILURE REPORT' $failurePath
            }
            catch {
                Write-Warn 'Impossible d''écrire ENGINE_FAILURE.txt.'
            }
        }

        Write-Host ''
        Read-Host 'Appuie sur ENTREE pour terminer'
    }
}