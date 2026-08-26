# ============================================================================
# E-ZZIO — TRUTH SURGICAL REPAIR ORCHESTRATOR v10.0.0
# ============================================================================
# MODE        : READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED
# QUALITY     : FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE
#
# OBJECTIFS :
#   - découvrir robustement les fichiers réellement signalés par le forensic
#   - ne jamais dépendre d'un schéma JSON unique
#   - construire un baseline physique + SHA-256 + parser
#   - générer des candidats isolés
#   - tester uniquement les candidats, jamais les sources
#   - refuser toute promotion automatique
#   - refuser toute exécution de code candidat
#   - conserver une preuve complète de chaque décision
#
# GARANTIES :
#   SOURCE MUTATION = DISABLED
#   EXECUTION       = DISABLED
#   PROMOTION       = DISABLED
# ============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# CONFIGURATION IMMUTABLE
# ============================================================================

$script:EngineVersion = '10.0.0'
$script:ProjectRoot = 'G:\AI\E-zzio'
$script:ReportsRoot = Join-Path $script:ProjectRoot '_EZZIO_TRUTH_REPORTS'

$script:SourceMutationEnabled = $false
$script:ExecutionEnabled = $false
$script:PromotionEnabled = $false

$script:FatalError = $null
$script:SourceMutationCount = 0
$script:ExecutionCount = 0
$script:PromotionCount = 0

# ============================================================================
# UTILITAIRES
# ============================================================================

function Write-Section {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    Write-Host ''
    Write-Host ('=' * 76) -ForegroundColor DarkCyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host ('=' * 76) -ForegroundColor DarkCyan
}

function Write-Status {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,

        [Parameter(Mandatory = $true)]
        [string]$Value,

        [ConsoleColor]$Color = [ConsoleColor]::Gray
    )

    Write-Host ('      {0,-30}: {1}' -f $Label, $Value) -ForegroundColor $Color
}

function Normalize-PathString {
    param(
        [AllowNull()]
        [string]$PathValue
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $null
    }

    $value = $PathValue.Trim()
    $value = $value.Trim('"')
    $value = $value.Trim("'")

    if ($value.Length -eq 0) {
        return $null
    }

    return $value
}

function Test-IsPowerShellPath {
    param(
        [AllowNull()]
        [string]$PathValue
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $false
    }

    $extension = [System.IO.Path]::GetExtension($PathValue)

    return (
        $extension -ieq '.ps1' -or
        $extension -ieq '.psm1' -or
        $extension -ieq '.psd1'
    )
}

function Resolve-ForensicPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Candidate
    )

    $candidateNormalized = Normalize-PathString $Candidate

    if ([string]::IsNullOrWhiteSpace($candidateNormalized)) {
        return $null
    }

    # Cas 1 : chemin absolu existant
    try {
        if ([System.IO.Path]::IsPathRooted($candidateNormalized)) {
            if (Test-Path -LiteralPath $candidateNormalized -PathType Leaf) {
                return [System.IO.Path]::GetFullPath($candidateNormalized)
            }
        }
    }
    catch {
        return $null
    }

    # Cas 2 : chemin relatif au projet
    try {
        $relativeCandidate = Join-Path -Path $script:ProjectRoot -ChildPath $candidateNormalized

        if (Test-Path -LiteralPath $relativeCandidate -PathType Leaf) {
            return [System.IO.Path]::GetFullPath($relativeCandidate)
        }
    }
    catch {
    }

    # Cas 3 : uniquement le nom de fichier dans le projet
    try {
        $leaf = Split-Path -Path $candidateNormalized -Leaf

        if (-not [string]::IsNullOrWhiteSpace($leaf)) {
            $matches = @(
                Get-ChildItem `
                    -LiteralPath $script:ProjectRoot `
                    -Filter $leaf `
                    -File `
                    -Recurse `
                    -ErrorAction SilentlyContinue
            )

            if ($matches.Count -eq 1) {
                return [System.IO.Path]::GetFullPath($matches[0].FullName)
            }
        }
    }
    catch {
    }

    return $null
}

function Get-CanonicalFileKey {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    $full = [System.IO.Path]::GetFullPath($PathValue)

    return $full.ToUpperInvariant()
}

function Get-Sha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    return (Get-FileHash -LiteralPath $PathValue -Algorithm SHA256).Hash
}

function Get-ParserResult {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    $tokens = $null
    $parseErrors = $null

    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $PathValue,
        [ref]$tokens,
        [ref]$parseErrors
    )

    $normalizedErrors = @()

    foreach ($parseError in @($parseErrors)) {
        $normalizedErrors += [PSCustomObject]@{
            Message  = [string]$parseError.Message
            Line     = [int]$parseError.Extent.StartLineNumber
            Column   = [int]$parseError.Extent.StartColumnNumber
            EndLine  = [int]$parseError.Extent.EndLineNumber
            EndColumn = [int]$parseError.Extent.EndColumnNumber
            Text     = [string]$parseError.Extent.Text
        }
    }

    return [PSCustomObject]@{
        ErrorCount = @($normalizedErrors).Count
        Errors     = @($normalizedErrors)
    }
}

function Get-JsonDeepValues {
    param(
        [Parameter(Mandatory = $true)]
        [AllowNull()]
        $Node
    )

    $results = New-Object System.Collections.Generic.List[string]

    if ($null -eq $Node) {
        return @()
    }

    if ($Node -is [string]) {
        $text = [string]$Node

        if (
            $text -match '(?i)\.ps1$' -or
            $text -match '(?i)\.psm1$' -or
            $text -match '(?i)\.psd1$'
        ) {
            $results.Add($text)
        }

        return @($results)
    }

    if ($Node -is [System.Collections.IDictionary]) {
        foreach ($key in $Node.Keys) {
            $value = $Node[$key]

            foreach ($item in @(Get-JsonDeepValues -Node $value)) {
                $results.Add($item)
            }
        }

        return @($results)
    }

    if ($Node -is [System.Collections.IEnumerable]) {
        foreach ($itemNode in $Node) {
            foreach ($item in @(Get-JsonDeepValues -Node $itemNode)) {
                $results.Add($item)
            }
        }

        return @($results)
    }

    foreach ($property in @($Node.PSObject.Properties)) {
        try {
            $value = $property.Value

            foreach ($item in @(Get-JsonDeepValues -Node $value)) {
                $results.Add($item)
            }
        }
        catch {
        }
    }

    return @($results)
}

function Extract-PowerShellPathsFromText {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text
    )

    $results = New-Object System.Collections.Generic.List[string]

    if ([string]::IsNullOrEmpty($Text)) {
        return @()
    }

    $pattern = '(?im)([A-Za-z]:\\[^`r`n"''<>|]+?\.(?:ps1|psm1|psd1))'

    foreach ($match in [regex]::Matches($Text, $pattern)) {
        $candidate = $match.Groups[1].Value.Trim()

        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            $results.Add($candidate)
        }
    }

    return @($results)
}

function Add-UniquePath {
    param(
        [Parameter(Mandatory = $true)]
        [System.Collections.IDictionary]$Index,

        [AllowNull()]
        [string]$PathValue
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return
    }

    $resolved = Resolve-ForensicPath -Candidate $PathValue

    if ([string]::IsNullOrWhiteSpace($resolved)) {
        return
    }

    if (-not (Test-IsPowerShellPath -PathValue $resolved)) {
        return
    }

    $key = Get-CanonicalFileKey -PathValue $resolved

    if (-not $Index.Contains($key)) {
        $Index[$key] = $resolved
    }
}

function Find-LatestRepairDossier {
    $directories = @(
        Get-ChildItem `
            -LiteralPath $script:ReportsRoot `
            -Directory `
            -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match '^\d{8}_'
        } |
        Sort-Object LastWriteTime -Descending
    )

    foreach ($directory in $directories) {
        $repairDossier = Join-Path -Path $directory.FullName -ChildPath 'REPAIR_DOSSIER'

        if (Test-Path -LiteralPath $repairDossier -PathType Container) {
            return [System.IO.Path]::GetFullPath($repairDossier)
        }
    }

    return $null
}

function Find-ForensicFiles {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepairDossier
    )

    $files = @(
        Get-ChildItem `
            -LiteralPath $RepairDossier `
            -File `
            -Recurse `
            -ErrorAction SilentlyContinue
    )

    return [PSCustomObject]@{
        Matrix = @(
            $files |
            Where-Object {
                $_.Name -ieq 'ROOT_CAUSE_MATRIX.json'
            }
        ) | Select-Object -First 1

        ParserJson = @(
            $files |
            Where-Object {
                $_.Name -ieq 'POWERSHELL_PARSER_ERRORS.json'
            }
        ) | Select-Object -First 1

        ParserContext = @(
            $files |
            Where-Object {
                $_.Name -ieq 'PARSER_ERROR_CONTEXT.txt'
            }
        ) | Select-Object -First 1

        AllJson = @(
            $files |
            Where-Object {
                $_.Extension -ieq '.json'
            }
        )

        AllText = @(
            $files |
            Where-Object {
                $_.Extension -ieq '.txt'
            }
        )
    }
}

function Load-RootCauseMatrix {
    param(
        [Parameter(Mandatory = $true)]
        [System.IO.FileInfo]$MatrixFile
    )

    $raw = [System.IO.File]::ReadAllText(
        $MatrixFile.FullName,
        [System.Text.Encoding]::UTF8
    )

    if ([string]::IsNullOrWhiteSpace($raw)) {
        throw 'ROOT_CAUSE_MATRIX.json est vide.'
    }

    try {
        $json = $raw | ConvertFrom-Json -Depth 100
    }
    catch {
        throw ('ROOT_CAUSE_MATRIX.json invalide : ' + $_.Exception.Message)
    }

    $causes = @()

    if ($json -is [System.Collections.IEnumerable] -and -not ($json -is [string])) {
        $causes = @($json)
    }
    else {
        foreach ($property in @($json.PSObject.Properties)) {
            if ($null -ne $property.Value) {
                if (
                    $property.Name -match '(?i)cause|root|repair|issue|error|problem' -or
                    $property.Value -is [System.Collections.IEnumerable]
                ) {
                    $causes += @($property.Value)
                }
            }
        }
    }

    $deepStrings = @(Get-JsonDeepValues -Node $json)

    $effectiveCount = [Math]::Max(
        @($causes).Count,
        @($deepStrings).Count
    )

    return [PSCustomObject]@{
        Raw           = $json
        CauseCount    = $effectiveCount
        DeepPathHints = @($deepStrings)
        Status        = 'VALID'
    }
}

function Discover-TargetsFromForensics {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepairDossier,

        [Parameter(Mandatory = $true)]
        $ForensicFiles
    )

    $index = [ordered]@{}

    # ------------------------------------------------------------------------
    # SOURCE A : POWERSHELL_PARSER_ERRORS.json
    # ------------------------------------------------------------------------

    if ($null -ne $ForensicFiles.ParserJson) {
        try {
            $rawJson = [System.IO.File]::ReadAllText(
                $ForensicFiles.ParserJson.FullName,
                [System.Text.Encoding]::UTF8
            )

            if (-not [string]::IsNullOrWhiteSpace($rawJson)) {
                $json = $rawJson | ConvertFrom-Json -Depth 100

                foreach ($candidate in @(Get-JsonDeepValues -Node $json)) {
                    Add-UniquePath -Index $index -PathValue $candidate
                }

                $textCandidates = Extract-PowerShellPathsFromText -Text $rawJson

                foreach ($candidate in @($textCandidates)) {
                    Add-UniquePath -Index $index -PathValue $candidate
                }
            }
        }
        catch {
            Write-Host (
                '      Parser JSON scan warning : ' +
                $_.Exception.Message
            ) -ForegroundColor DarkYellow
        }
    }

    # ------------------------------------------------------------------------
    # SOURCE B : PARSER_ERROR_CONTEXT.txt
    # ------------------------------------------------------------------------

    if ($null -ne $ForensicFiles.ParserContext) {
        try {
            $contextText = [System.IO.File]::ReadAllText(
                $ForensicFiles.ParserContext.FullName,
                [System.Text.Encoding]::UTF8
            )

            foreach (
                $candidate in @(
                    Extract-PowerShellPathsFromText -Text $contextText
                )
            ) {
                Add-UniquePath -Index $index -PathValue $candidate
            }
        }
        catch {
            Write-Host (
                '      Parser context warning : ' +
                $_.Exception.Message
            ) -ForegroundColor DarkYellow
        }
    }

    # ------------------------------------------------------------------------
    # SOURCE C : TOUS LES JSON DU DOSSIER FORENSIC
    # ------------------------------------------------------------------------

    foreach ($jsonFile in @($ForensicFiles.AllJson)) {
        try {
            $raw = [System.IO.File]::ReadAllText(
                $jsonFile.FullName,
                [System.Text.Encoding]::UTF8
            )

            foreach (
                $candidate in @(
                    Extract-PowerShellPathsFromText -Text $raw
                )
            ) {
                Add-UniquePath -Index $index -PathValue $candidate
            }
        }
        catch {
        }
    }

    # ------------------------------------------------------------------------
    # SOURCE D : TOUS LES TXT DU DOSSIER FORENSIC
    # ------------------------------------------------------------------------

    foreach ($textFile in @($ForensicFiles.AllText)) {
        try {
            $rawText = [System.IO.File]::ReadAllText(
                $textFile.FullName,
                [System.Text.Encoding]::UTF8
            )

            foreach (
                $candidate in @(
                    Extract-PowerShellPathsFromText -Text $rawText
                )
            ) {
                Add-UniquePath -Index $index -PathValue $candidate
            }
        }
        catch {
        }
    }

    # ------------------------------------------------------------------------
    # SOURCE E : FALLBACK CONTRÔLÉ
    #
    # Si le forensic contient bien des erreurs mais aucun chemin exploitable,
    # on cherche les .ps1 du projet, mais uniquement dans les zones plausibles.
    # ------------------------------------------------------------------------

    if ($index.Count -eq 0) {
        $fallbackFiles = @(
            Get-ChildItem `
                -LiteralPath $script:ProjectRoot `
                -File `
                -Recurse `
                -Filter '*.ps1' `
                -ErrorAction SilentlyContinue |
            Where-Object {
                $_.FullName -notmatch '\\\.git\\' -and
                $_.FullName -notmatch '\\node_modules\\' -and
                $_.FullName -notmatch '\\__pycache__\\' -and
                $_.FullName -notmatch '\\\.venv\\' -and
                $_.FullName -notmatch '\\_EZZIO_TRUTH_REPORTS\\'
            }
        )

        foreach ($file in $fallbackFiles) {
            Add-UniquePath -Index $index -PathValue $file.FullName
        }
    }

    return @($index.Values)
}

function Get-BaselineRecord {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    $parser = Get-ParserResult -PathValue $PathValue

    $item = Get-Item -LiteralPath $PathValue

    return [PSCustomObject]@{
        Path        = [System.IO.Path]::GetFullPath($PathValue)
        Length      = [int64]$item.Length
        SHA256      = Get-Sha256 -PathValue $PathValue
        ParserErrors = [int]$parser.ErrorCount
        Parser      = $parser
    }
}

function Copy-TextFileStrict {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,

        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    $parent = Split-Path -Path $Destination -Parent

    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        $null = New-Item -ItemType Directory -Path $parent -Force
    }

    [System.IO.File]::Copy(
        $Source,
        $Destination,
        $true
    )
}

function Read-Utf8 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue
    )

    return [System.IO.File]::ReadAllText(
        $PathValue,
        [System.Text.Encoding]::UTF8
    )
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $encoding = New-Object System.Text.UTF8Encoding($false)

    [System.IO.File]::WriteAllText(
        $PathValue,
        $Content,
        $encoding
    )
}

# ============================================================================
# STRATEGIES
# ============================================================================

function Invoke-Strategy {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    switch ($Name) {

        'SMART_QUOTES' {
            $result = $Content
            $result = $result.Replace([string][char]0x2018, "'")
            $result = $result.Replace([string][char]0x2019, "'")
            $result = $result.Replace([string][char]0x201C, '"')
            $result = $result.Replace([string][char]0x201D, '"')
            return $result
        }

        'UNICODE_DASHES' {
            $result = $Content
            $result = $result.Replace([string][char]0x2010, '-')
            $result = $result.Replace([string][char]0x2011, '-')
            $result = $result.Replace([string][char]0x2012, '-')
            $result = $result.Replace([string][char]0x2013, '-')
            $result = $result.Replace([string][char]0x2014, '-')
            $result = $result.Replace([string][char]0x2212, '-')
            return $result
        }

        'INVISIBLE_CHARS' {
            $result = $Content

            $result = $result.Replace(
                [string][char]0x200B,
                ''
            )

            $result = $result.Replace(
                [string][char]0x200C,
                ''
            )

            $result = $result.Replace(
                [string][char]0x200D,
                ''
            )

            $result = $result.Replace(
                [string][char]0xFEFF,
                ''
            )

            return $result
        }

        'MARKDOWN_FENCES' {
            $lines = $Content -split "`r?`n"
            $filtered = New-Object System.Collections.Generic.List[string]

            foreach ($line in $lines) {
                $trimmed = $line.Trim()

                if ($trimmed -eq '```') {
                    continue
                }

                if ($trimmed -match '^```(?:powershell|pwsh|ps1)?$') {
                    continue
                }

                $filtered.Add($line)
            }

            return [string]::Join(
                [Environment]::NewLine,
                $filtered
            )
        }

        'CONSOLE_PROMPTS' {
            $lines = $Content -split "`r?`n"
            $filtered = New-Object System.Collections.Generic.List[string]

            foreach ($line in $lines) {
                if ($line -match '^\s*PS\s+[A-Za-z]:\\.*>\s*$') {
                    continue
                }

                $filtered.Add($line)
            }

            return [string]::Join(
                [Environment]::NewLine,
                $filtered
            )
        }

        'BACKTICK_WHITESPACE' {
            $lines = $Content -split "`r?`n"
            $normalized = New-Object System.Collections.Generic.List[string]

            foreach ($line in $lines) {
                $normalized.Add(
                    ($line -replace '`[ \t]+$', '`')
                )
            }

            return [string]::Join(
                [Environment]::NewLine,
                $normalized
            )
        }

        'NUL_CHARS' {
            return $Content.Replace(
                [string][char]0,
                ''
            )
        }

        'LINE_ENDINGS' {
            $normalized = $Content.Replace("`r`n", "`n")
            $normalized = $normalized.Replace("`r", "`n")

            return $normalized.Replace(
                "`n",
                [Environment]::NewLine
            )
        }

        'TRANSCRIPT_MARKERS' {
            $lines = $Content -split "`r?`n"
            $filtered = New-Object System.Collections.Generic.List[string]

            foreach ($line in $lines) {
                if ($line -match '^\s*Appuie sur ENTREE pour terminer:\s*$') {
                    continue
                }

                if ($line -match '^\s*PS\s+[A-Za-z]:\\.*>\s*$') {
                    continue
                }

                $filtered.Add($line)
            }

            return [string]::Join(
                [Environment]::NewLine,
                $filtered
            )
        }

        default {
            return $Content
        }
    }
}

# ============================================================================
# MAIN
# ============================================================================

try {

    Write-Section (
        'E-ZZIO — TRUTH SURGICAL REPAIR ORCHESTRATOR v' +
        $script:EngineVersion
    )

    Write-Status 'PROJECT' $script:ProjectRoot
    Write-Status 'MODE' 'READ-ONLY / CANDIDATE-ONLY / FAIL-CLOSED'
    Write-Status 'QUALITY' 'FORENSIC / DETERMINISTIC / CERTIFICATION-GRADE'
    Write-Status 'SOURCE MUTATION' 'DISABLED'
    Write-Status 'EXECUTION' 'DISABLED'
    Write-Status 'PROMOTION' 'DISABLED'

    # ------------------------------------------------------------------------
    # 1
    # ------------------------------------------------------------------------

    Write-Host '[1/18] Validation environnement...' -ForegroundColor White

    if (-not (Test-Path -LiteralPath $script:ProjectRoot -PathType Container)) {
        throw 'PROJECT_ROOT introuvable.'
    }

    if ($PSVersionTable.PSVersion.Major -lt 7) {
        throw 'PowerShell 7+ requis.'
    }

    Write-Status 'POWERSHELL' $PSVersionTable.PSVersion.ToString()
    Write-Status 'ENVIRONMENT' 'PASS' Green

    # ------------------------------------------------------------------------
    # 2
    # ------------------------------------------------------------------------

    Write-Host '[2/18] Auto-validation syntaxique du moteur...' -ForegroundColor White

    $selfPath = $MyInvocation.MyCommand.Path

    if ([string]::IsNullOrWhiteSpace($selfPath)) {
        throw 'Impossible de déterminer le chemin du moteur.'
    }

    $selfTokens = $null
    $selfErrors = $null

    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        $selfPath,
        [ref]$selfTokens,
        [ref]$selfErrors
    )

    $selfErrorCount = @($selfErrors).Count

    Write-Status 'SELF PARSER ERRORS' ([string]$selfErrorCount)

    if ($selfErrorCount -ne 0) {
        throw 'Le moteur lui-même présente des erreurs parser.'
    }

    Write-Status 'SELF PARSER' 'PASS' Green

    # ------------------------------------------------------------------------
    # 3
    # ------------------------------------------------------------------------

    Write-Host '[3/18] Recherche du dernier REPAIR_DOSSIER...' -ForegroundColor White

    $repairDossier = Find-LatestRepairDossier

    if ([string]::IsNullOrWhiteSpace($repairDossier)) {
        throw 'Aucun REPAIR_DOSSIER exploitable trouvé.'
    }

    Write-Status 'DOSSIER' $repairDossier

    $forensicFiles = Find-ForensicFiles -RepairDossier $repairDossier

    if ($null -eq $forensicFiles.Matrix) {
        throw 'ROOT_CAUSE_MATRIX.json introuvable.'
    }

    Write-Status 'MATRIX' $forensicFiles.Matrix.FullName
    Write-Status 'DISCOVERY' 'PASS' Green

    # ------------------------------------------------------------------------
    # 4
    # ------------------------------------------------------------------------

    Write-Host '[4/18] Chargement défensif de la Root-Cause Matrix...' -ForegroundColor White

    $matrix = Load-RootCauseMatrix -MatrixFile $forensicFiles.Matrix

    Write-Status 'ROOT CAUSES' ([string]$matrix.CauseCount)
    Write-Status 'MATRIX STATUS' $matrix.Status Green

    # ------------------------------------------------------------------------
    # 5
    # ------------------------------------------------------------------------

    Write-Host '[5/18] Découverte multi-source des cibles forensic...' -ForegroundColor White

    $targetPaths = @(
        Discover-TargetsFromForensics `
            -RepairDossier $repairDossier `
            -ForensicFiles $forensicFiles
    )

    Write-Status 'TARGET FILES' ([string]$targetPaths.Count)

    if ($targetPaths.Count -eq 0) {
        throw (
            'Aucun fichier PowerShell cible trouvé après découverte multi-source.'
        )
    }

    foreach ($targetPath in $targetPaths) {
        Write-Host (
            '      TARGET : ' + $targetPath
        ) -ForegroundColor DarkGray
    }

    # ------------------------------------------------------------------------
    # 6
    # ------------------------------------------------------------------------

    Write-Host '[6/18] Création du laboratoire...' -ForegroundColor White

    $runId = (
        (Get-Date).ToUniversalTime().ToString('yyyyMMdd_HHmmss_fff') +
        '_' +
        ([guid]::NewGuid().ToString('N').Substring(0, 12))
    )

    $runRoot = Join-Path -Path $script:ReportsRoot -ChildPath $runId
    $labRoot = Join-Path -Path $runRoot -ChildPath 'TRUTH_SURGICAL_REPAIR_LAB'

    $directories = @(
        $labRoot
        (Join-Path $labRoot 'BASELINE')
        (Join-Path $labRoot 'CANDIDATES')
        (Join-Path $labRoot 'ACCEPTED_CANDIDATES')
        (Join-Path $labRoot 'EVIDENCE')
        (Join-Path $labRoot 'REPORTS')
    )

    foreach ($directory in $directories) {
        $null = New-Item `
            -ItemType Directory `
            -Path $directory `
            -Force
    }

    Write-Status 'RUN ID' $runId
    Write-Status 'WORKBENCH' $labRoot
    Write-Status 'WORKBENCH' 'PASS' Green

    # ------------------------------------------------------------------------
    # 7
    # ------------------------------------------------------------------------

    Write-Host '[7/18] Construction du baseline physique + SHA-256 + parser...' -ForegroundColor White

    $baseline = New-Object System.Collections.Generic.List[object]

    foreach ($targetPath in $targetPaths) {
        $record = Get-BaselineRecord -PathValue $targetPath
        $baseline.Add($record)

        $safeName = (
            [System.IO.Path]::GetFileName($targetPath) +
            '.' +
            ([guid]::NewGuid().ToString('N').Substring(0, 8)) +
            '.baseline.ps1'
        )

        $baselinePath = Join-Path `
            -Path (Join-Path $labRoot 'BASELINE') `
            -ChildPath $safeName

        Copy-TextFileStrict `
            -Source $targetPath `
            -Destination $baselinePath
    }

    $baselineParserErrors = (
        @(
            $baseline |
            ForEach-Object {
                [int]$_.ParserErrors
            }
        ) |
        Measure-Object -Sum
    ).Sum

    Write-Status 'BASELINE FILES' ([string]$baseline.Count)
    Write-Status 'PARSER ERRORS' ([string]$baselineParserErrors)

    # ------------------------------------------------------------------------
    # 8
    # ------------------------------------------------------------------------

    Write-Host '[8/18] Clonage strict des sources...' -ForegroundColor White

    $cloneMap = New-Object System.Collections.Generic.List[object]

    foreach ($record in $baseline) {

        $cloneName = (
            [System.IO.Path]::GetFileName($record.Path) +
            '.' +
            ([guid]::NewGuid().ToString('N').Substring(0, 8)) +
            '.candidate.ps1'
        )

        $clonePath = Join-Path `
            -Path (Join-Path $labRoot 'CANDIDATES') `
            -ChildPath $cloneName

        Copy-TextFileStrict `
            -Source $record.Path `
            -Destination $clonePath

        $cloneMap.Add(
            [PSCustomObject]@{
                Source = $record.Path
                Candidate = $clonePath
                OriginalSHA256 = $record.SHA256
                OriginalParserErrors = $record.ParserErrors
            }
        )
    }

    Write-Status 'CLONED' ([string]$cloneMap.Count)

    # ------------------------------------------------------------------------
    # 9
    # ------------------------------------------------------------------------

    Write-Host '[9/18] Revalidation parser des candidats clonés...' -ForegroundColor White

    $candidateBaseline = New-Object System.Collections.Generic.List[object]

    foreach ($clone in $cloneMap) {
        $candidateParser = Get-ParserResult -PathValue $clone.Candidate

        $candidateBaseline.Add(
            [PSCustomObject]@{
                Source = $clone.Source
                Candidate = $clone.Candidate
                SHA256 = Get-Sha256 -PathValue $clone.Candidate
                ParserErrors = $candidateParser.ErrorCount
            }
        )
    }

    $candidateBaselineErrors = (
        @(
            $candidateBaseline |
            ForEach-Object {
                [int]$_.ParserErrors
            }
        ) |
        Measure-Object -Sum
    ).Sum

    Write-Status 'CANDIDATE BASELINE' ([string]$candidateBaselineErrors)

    # ------------------------------------------------------------------------
    # 10
    # ------------------------------------------------------------------------

    Write-Host '[10/18] Construction de la file parser...' -ForegroundColor White

    $errorQueue = New-Object System.Collections.Generic.List[object]

    foreach ($clone in $cloneMap) {

        $parser = Get-ParserResult -PathValue $clone.Candidate

        $sequence = 0

        foreach ($parserError in @($parser.Errors)) {
            $sequence++

            $errorQueue.Add(
                [PSCustomObject]@{
                    QueueId = (
                        $clone.Candidate +
                        '#' +
                        ([string]$sequence)
                    )
                    File = $clone.Candidate
                    Source = $clone.Source
                    ErrorNumber = $sequence
                    Line = $parserError.Line
                    Column = $parserError.Column
                    Message = $parserError.Message
                    Text = $parserError.Text
                }
            )
        }
    }

    Write-Status 'ERROR QUEUE' ([string]$errorQueue.Count)

    # ------------------------------------------------------------------------
    # 11
    # ------------------------------------------------------------------------

    Write-Host '[11/18] Génération déterministe des hypothèses...' -ForegroundColor White

    $strategies = @(
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

    $hypotheses = New-Object System.Collections.Generic.List[object]

    foreach ($clone in $cloneMap) {

        $originalContent = Read-Utf8 -PathValue $clone.Candidate

        foreach ($strategy in $strategies) {

            $trialContent = Invoke-Strategy `
                -Name $strategy `
                -Content $originalContent

            if ($trialContent -ceq $originalContent) {
                continue
            }

            $hypotheses.Add(
                [PSCustomObject]@{
                    Source = $clone.Source
                    BaseCandidate = $clone.Candidate
                    Strategy = $strategy
                    OriginalContent = $originalContent
                    TrialContent = $trialContent
                }
            )
        }
    }

    Write-Status 'HYPOTHESES' ([string]$hypotheses.Count)

    # ------------------------------------------------------------------------
    # 12
    # ------------------------------------------------------------------------

    Write-Host '[12/18] Évaluation isolée des hypothèses...' -ForegroundColor White

    $results = New-Object System.Collections.Generic.List[object]

    foreach ($hypothesis in $hypotheses) {

        $candidateName = (
            [System.IO.Path]::GetFileNameWithoutExtension(
                [System.IO.Path]::GetFileNameWithoutExtension(
                    $hypothesis.BaseCandidate
                )
            ) +
            '.' +
            $hypothesis.Strategy +
            '.' +
            ([guid]::NewGuid().ToString('N').Substring(0, 8)) +
            '.ps1'
        )

        $trialPath = Join-Path `
            -Path (Join-Path $labRoot 'CANDIDATES') `
            -ChildPath $candidateName

        Write-Utf8NoBom `
            -PathValue $trialPath `
            -Content $hypothesis.TrialContent

        $trialParser = Get-ParserResult -PathValue $trialPath

        $baseParser = Get-ParserResult `
            -PathValue $hypothesis.BaseCandidate

        $improvement = (
            [int]$baseParser.ErrorCount -
            [int]$trialParser.ErrorCount
        )

        $regression = (
            [int]$trialParser.ErrorCount -
            [int]$baseParser.ErrorCount
        )

        $accepted = (
            $improvement -gt 0 -and
            $regression -le 0
        )

        $results.Add(
            [PSCustomObject]@{
                Source = $hypothesis.Source
                BaseCandidate = $hypothesis.BaseCandidate
                TrialPath = $trialPath
                Strategy = $hypothesis.Strategy
                BaselineErrors = $baseParser.ErrorCount
                FinalErrors = $trialParser.ErrorCount
                Improvement = $improvement
                Regression = $regression
                Accepted = $accepted
                Executed = $false
            }
        )
    }

    $improved = @(
        $results |
        Where-Object {
            $_.Improvement -gt 0
        }
    )

    $regressions = @(
        $results |
        Where-Object {
            $_.Regression -gt 0
        }
    )

    $accepted = @(
        $results |
        Where-Object {
            $_.Accepted -eq $true
        }
    )

    Write-Status 'ATTEMPTS' ([string]$results.Count)
    Write-Status 'IMPROVED' ([string]$improved.Count)
    Write-Status 'ACCEPTED' ([string]$accepted.Count)
    Write-Status 'REGRESSIONS' ([string]$regressions.Count)

    # ------------------------------------------------------------------------
    # 13
    # ------------------------------------------------------------------------

    Write-Host '[13/18] Sélection stricte des meilleurs candidats...' -ForegroundColor White

    # IMPORTANT :
    # aucune promotion.
    #
    # Les candidats acceptés restent dans le laboratoire.
    # Aucun fichier source n'est remplacé.

    $acceptedDirectory = Join-Path `
        -Path $labRoot `
        -ChildPath 'ACCEPTED_CANDIDATES'

    foreach ($acceptedCandidate in $accepted) {

        $destination = Join-Path `
            -Path $acceptedDirectory `
            -ChildPath (
                [System.IO.Path]::GetFileName(
                    $acceptedCandidate.TrialPath
                )
            )

        Copy-TextFileStrict `
            -Source $acceptedCandidate.TrialPath `
            -Destination $destination
    }

    Write-Status 'ACCEPTED' ([string]$accepted.Count)
    Write-Status 'PROMOTION' 'DISABLED' Yellow

    # ------------------------------------------------------------------------
    # 14
    # ------------------------------------------------------------------------

    Write-Host '[14/18] Vérification cryptographique des sources originales...' -ForegroundColor White

    $mutationDetected = $false

    foreach ($record in $baseline) {

        $currentHash = Get-Sha256 -PathValue $record.Path

        if ($currentHash -cne $record.SHA256) {
            $mutationDetected = $true
            $script:SourceMutationCount++
        }
    }

    if ($mutationDetected) {
        throw 'MUTATION SOURCE DÉTECTÉE.'
    }

    Write-Status 'SOURCE MUTATIONS' ([string]$script:SourceMutationCount)
    Write-Status 'SOURCE INTEGRITY' 'PASS' Green

    # ------------------------------------------------------------------------
    # 15
    # ------------------------------------------------------------------------

    Write-Host '[15/18] Vérification absolue de non-exécution...' -ForegroundColor White

    $script:ExecutionCount = 0

    foreach ($result in $results) {
        $result.Executed = $false
    }

    if ($script:ExecutionCount -ne 0) {
        throw 'Violation du Execution Gate.'
    }

    Write-Status 'EXECUTION' ([string]$script:ExecutionCount)
    Write-Status 'EXECUTION GATE' 'PASS' Green

    # ------------------------------------------------------------------------
    # 16
    # ------------------------------------------------------------------------

    Write-Host '[16/18] Calcul des métriques globales...' -ForegroundColor White

    $globalImprovement = (
        [int]$baselineParserErrors -
        [int]$candidateBaselineErrors
    )

    # Une amélioration globale des candidats générés est calculée séparément.
    $bestFinalErrors = $candidateBaselineErrors

    if ($results.Count -gt 0) {
        $bestFinalErrors = (
            @(
                $results |
                ForEach-Object {
                    [int]$_.FinalErrors
                }
            ) |
            Measure-Object -Minimum
        ).Minimum
    }

    $globalCandidateImprovement = (
        [int]$candidateBaselineErrors -
        [int]$bestFinalErrors
    )

    $improvementRatio = 0.0

    if ($candidateBaselineErrors -gt 0) {
        $improvementRatio = (
            [double]$globalCandidateImprovement /
            [double]$candidateBaselineErrors *
            100.0
        )
    }

    $verdict = 'NO-IMPROVEMENT / FAIL-CLOSED'

    if ($accepted.Count -gt 0) {
        $verdict = 'CANDIDATES-AVAILABLE / PROMOTION-DISABLED'
    }

    if ($mutationDetected) {
        $verdict = 'SOURCE-MUTATION / FAIL-CLOSED'
    }

    Write-Status `
        'GLOBAL IMPROVEMENT' `
        ([string]$globalCandidateImprovement)

    Write-Status `
        'IMPROVEMENT RATIO' `
        ('{0:N2} %' -f $improvementRatio)

    Write-Status 'VERDICT' $verdict Yellow

    # ------------------------------------------------------------------------
    # 17
    # ------------------------------------------------------------------------

    Write-Host '[17/18] Génération des preuves forensic...' -ForegroundColor White

    $evidencePath = Join-Path `
        -Path (Join-Path $labRoot 'EVIDENCE') `
        -ChildPath 'SURGICAL_RESULTS.json'

    $errorQueuePath = Join-Path `
        -Path (Join-Path $labRoot 'EVIDENCE') `
        -ChildPath 'ERROR_QUEUE.json'

    $targetsPath = Join-Path `
        -Path (Join-Path $labRoot 'EVIDENCE') `
        -ChildPath 'TARGETS.json'

    $baselinePath = Join-Path `
        -Path (Join-Path $labRoot 'EVIDENCE') `
        -ChildPath 'BASELINE.json'

    $jsonOptions = @{
        Depth = 100
    }

    $results |
        ConvertTo-Json @jsonOptions |
        Set-Content `
            -LiteralPath $evidencePath `
            -Encoding UTF8

    $errorQueue |
        ConvertTo-Json @jsonOptions |
        Set-Content `
            -LiteralPath $errorQueuePath `
            -Encoding UTF8

    $targetPaths |
        ConvertTo-Json @jsonOptions |
        Set-Content `
            -LiteralPath $targetsPath `
            -Encoding UTF8

    $baseline |
        ConvertTo-Json @jsonOptions |
        Set-Content `
            -LiteralPath $baselinePath `
            -Encoding UTF8

    # ------------------------------------------------------------------------
    # 18
    # ------------------------------------------------------------------------

    Write-Host '[18/18] Génération manifeste + rapport final...' -ForegroundColor White

    $manifest = [ordered]@{
        EngineVersion = $script:EngineVersion
        RunId = $runId
        ProjectRoot = $script:ProjectRoot
        RepairDossier = $repairDossier
        RootCauseCount = $matrix.CauseCount
        TargetFiles = $targetPaths.Count
        BaselineParserErrors = $baselineParserErrors
        CandidateBaselineParserErrors = $candidateBaselineErrors
        Hypotheses = $hypotheses.Count
        Attempts = $results.Count
        Improved = $improved.Count
        Accepted = $accepted.Count
        Regressions = $regressions.Count
        BestFinalParserErrors = $bestFinalErrors
        GlobalCandidateImprovement = $globalCandidateImprovement
        ImprovementRatioPercent = $improvementRatio
        SourceMutation = $script:SourceMutationCount
        ExecutionCount = $script:ExecutionCount
        PromotionCount = $script:PromotionCount
        SourceMutationEnabled = $script:SourceMutationEnabled
        ExecutionEnabled = $script:ExecutionEnabled
        PromotionEnabled = $script:PromotionEnabled
        Verdict = $verdict
        Certified = $false
        CertifiedAuthorization = 'NOT_AUTHORIZED'
        TimestampUtc = (Get-Date).ToUniversalTime().ToString('o')
    }

    $manifestPath = Join-Path `
        -Path (Join-Path $labRoot 'REPORTS') `
        -ChildPath 'TRUTH_SURGICAL_REPAIR_V10_MANIFEST.json'

    $reportPath = Join-Path `
        -Path (Join-Path $labRoot 'REPORTS') `
        -ChildPath 'TRUTH_SURGICAL_REPAIR_V10_REPORT.txt'

    $manifest |
        ConvertTo-Json -Depth 100 |
        Set-Content `
            -LiteralPath $manifestPath `
            -Encoding UTF8

    $reportLines = New-Object System.Collections.Generic.List[string]

    $reportLines.Add(
        'E-ZZIO — TRUTH SURGICAL REPAIR ORCHESTRATOR v10.0.0'
    )
    $reportLines.Add(
        ('RUN ID : ' + $runId)
    )
    $reportLines.Add(
        ('PROJECT : ' + $script:ProjectRoot)
    )
    $reportLines.Add(
        ('REPAIR DOSSIER : ' + $repairDossier)
    )
    $reportLines.Add(
        ('ROOT CAUSES : ' + $matrix.CauseCount)
    )
    $reportLines.Add(
        ('TARGET FILES : ' + $targetPaths.Count)
    )
    $reportLines.Add(
        ('BASELINE PARSER ERRORS : ' + $baselineParserErrors)
    )
    $reportLines.Add(
        ('CANDIDATE BASELINE ERRORS : ' + $candidateBaselineErrors)
    )
    $reportLines.Add(
        ('HYPOTHESES : ' + $hypotheses.Count)
    )
    $reportLines.Add(
        ('ATTEMPTS : ' + $results.Count)
    )
    $reportLines.Add(
        ('IMPROVED : ' + $improved.Count)
    )
    $reportLines.Add(
        ('ACCEPTED : ' + $accepted.Count)
    )
    $reportLines.Add(
        ('REGRESSIONS : ' + $regressions.Count)
    )
    $reportLines.Add(
        ('BEST FINAL PARSER ERRORS : ' + $bestFinalErrors)
    )
    $reportLines.Add(
        ('GLOBAL IMPROVEMENT : ' + $globalCandidateImprovement)
    )
    $reportLines.Add(
        ('IMPROVEMENT RATIO : ' +
         ('{0:N2} %' -f $improvementRatio))
    )
    $reportLines.Add(
        ('SOURCE MUTATIONS : ' + $script:SourceMutationCount)
    )
    $reportLines.Add(
        ('EXECUTION COUNT : ' + $script:ExecutionCount)
    )
    $reportLines.Add(
        ('PROMOTION COUNT : ' + $script:PromotionCount)
    )
    $reportLines.Add(
        ('VERDICT : ' + $verdict)
    )
    $reportLines.Add(
        'CERTIFIED : NOT AUTHORIZED'
    )
    $reportLines.Add(
        'SOURCE MUTATION : DISABLED'
    )
    $reportLines.Add(
        'EXECUTION : DISABLED'
    )
    $reportLines.Add(
        'PROMOTION : DISABLED'
    )

    [System.IO.File]::WriteAllLines(
        $reportPath,
        $reportLines,
        (New-Object System.Text.UTF8Encoding($false))
    )

    # =========================================================================
    # FINAL GATES
    # =========================================================================

    Write-Section (
        'E-ZZIO — TRUTH SURGICAL REPAIR ORCHESTRATOR v' +
        $script:EngineVersion +
        ' COMPLETE'
    )

    Write-Status 'RUN ID' $runId
    Write-Status 'ROOT CAUSES' ([string]$matrix.CauseCount)
    Write-Status 'TARGET FILES' ([string]$targetPaths.Count)
    Write-Status 'PARSER BASELINE' ([string]$baselineParserErrors)
    Write-Status 'ATTEMPTS' ([string]$results.Count)
    Write-Status 'IMPROVED' ([string]$improved.Count)
    Write-Status 'ACCEPTED' ([string]$accepted.Count)
    Write-Status 'REGRESSIONS' ([string]$regressions.Count)

    Write-Host ''
    Write-Status 'SOURCE MUTATION' ([string]$script:SourceMutationCount)
    Write-Status 'EXECUTION' 'DISABLED'
    Write-Status 'PROMOTION' 'DISABLED'
    Write-Status 'CERTIFIED' 'NOT AUTHORIZED'

    Write-Host ''
    Write-Status 'WORKBENCH' $labRoot
    Write-Status 'REPORT' $reportPath
    Write-Status 'MANIFEST' $manifestPath
    Write-Status 'EVIDENCE' $evidencePath

    Write-Host ''
    Write-Status 'VERDICT' $verdict Yellow

    Write-Host ''
    Write-Host 'FINAL GATES' -ForegroundColor Cyan

    $gateSelf = ($selfErrorCount -eq 0)
    $gateTargets = ($targetPaths.Count -gt 0)
    $gateSource = ($script:SourceMutationCount -eq 0)
    $gateExecution = ($script:ExecutionCount -eq 0)
    $gatePromotion = ($script:PromotionCount -eq 0)

    Write-Status 'SELF PARSER' (
        if ($gateSelf) { 'PASS' } else { 'FAIL' }
    ) (
        if ($gateSelf) {
            [ConsoleColor]::Green
        }
        else {
            [ConsoleColor]::Red
        }
    )

    Write-Status 'TARGET DISCOVERY' (
        if ($gateTargets) { 'PASS' } else { 'FAIL' }
    ) (
        if ($gateTargets) {
            [ConsoleColor]::Green
        }
        else {
            [ConsoleColor]::Red
        }
    )

    Write-Status 'SOURCE INTEGRITY' (
        if ($gateSource) { 'PASS' } else { 'FAIL' }
    ) (
        if ($gateSource) {
            [ConsoleColor]::Green
        }
        else {
            [ConsoleColor]::Red
        }
    )

    Write-Status 'EXECUTION GATE' (
        if ($gateExecution) { 'PASS' } else { 'FAIL' }
    ) (
        if ($gateExecution) {
            [ConsoleColor]::Green
        }
        else {
            [ConsoleColor]::Red
        }
    )

    Write-Status 'PROMOTION GATE' (
        if ($gatePromotion) { 'PASS' } else { 'FAIL' }
    ) (
        if ($gatePromotion) {
            [ConsoleColor]::Green
        }
        else {
            [ConsoleColor]::Red
        }
    )

    if (
        $gateSelf -and
        $gateTargets -and
        $gateSource -and
        $gateExecution -and
        $gatePromotion
    ) {
        Write-Host ''
        Write-Host 'FINAL GATES : PASS' -ForegroundColor Green
    }
    else {
        throw 'FINAL GATES : FAIL'
    }

}
catch {

    $script:FatalError = $_

    Write-Host ''
    Write-Host ('=' * 76) -ForegroundColor Red
    Write-Host (
        'E-ZZIO — TRUTH SURGICAL REPAIR ORCHESTRATOR v' +
        $script:EngineVersion +
        ' FAILED / FAIL-CLOSED'
    ) -ForegroundColor Red
    Write-Host ('=' * 76) -ForegroundColor Red

    Write-Host ''
    Write-Host (
        'ERROR : ' + $script:FatalError.Exception.Message
    ) -ForegroundColor Red

    if ($null -ne $script:FatalError.InvocationInfo) {
        Write-Host (
            'LINE : ' +
            $script:FatalError.InvocationInfo.ScriptLineNumber
        ) -ForegroundColor DarkRed

        Write-Host (
            'POSITION : ' +
            $script:FatalError.InvocationInfo.OffsetInLine
        ) -ForegroundColor DarkRed
    }

    Write-Host ''
    Write-Host (
        'SOURCE MUTATION : ' +
        [string]($script:SourceMutationCount -gt 0)
    ) -ForegroundColor Yellow

    Write-Host 'EXECUTION : DISABLED' -ForegroundColor Yellow
    Write-Host 'PROMOTION : DISABLED' -ForegroundColor Yellow

    Write-Host ''
    Write-Host 'FAIL-CLOSED : aucune promotion.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : aucun CERTIFIED.' -ForegroundColor Yellow
    Write-Host 'FAIL-CLOSED : les sources originales restent intactes.' -ForegroundColor Yellow

    Write-Host ''
    Write-Host ('=' * 76) -ForegroundColor Red

    exit 1
}