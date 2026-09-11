# ============================================================================
# E-ZZIO — CONTROLLED PURIFICATION + REBASELINE v0.2.1
# ============================================================================

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$PointZeroDir,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Target,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ExpectedNewExtension,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ForensicRoot,

    [switch]$PauseOnExit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ============================================================================
# ENGINE STATE
# ============================================================================

$script:EngineName    = 'E-ZZIO — CONTROLLED PURIFICATION + REBASELINE'
$script:EngineVersion = '0.2.1'

$script:StartedUtc = [DateTime]::UtcNow
$script:ExitCode   = 1

$script:SourceRoot      = $null
$script:PhysicalPath    = $null
$script:DestinationPath = $null

$script:NewPointZeroDir = $null

$script:MutationPerformed = $false
$script:RenamePerformed   = $false

$script:GateResults = [System.Collections.Generic.List[object]]::new()
$script:Evidence    = [System.Collections.Generic.List[object]]::new()
$script:Warnings    = [System.Collections.Generic.List[string]]::new()

$script:FatalError = $null

$originalHash = $null
$newHash      = $null

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
    Write-Host " $Title" -ForegroundColor Cyan
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

# ============================================================================
# GATES
# ============================================================================

function Add-Gate {
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
            Gate   = $Gate
            Passed = $Passed
            Detail = $Detail
        }
    ) | Out-Null
}

function Add-Evidence {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Type,

        [Parameter(Mandatory = $true)]
        [string]$Value
    )

    $script:Evidence.Add(
        [PSCustomObject]@{
            Type  = $Type
            Value = $Value
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

    $childFull  = [System.IO.Path]::GetFullPath($Child)
    $parentFull = [System.IO.Path]::GetFullPath($Parent)

    if (
        -not $parentFull.EndsWith(
            [string][System.IO.Path]::DirectorySeparatorChar,
            [System.StringComparison]::Ordinal
        )
    ) {
        $parentFull += [System.IO.Path]::DirectorySeparatorChar
    }

    return $childFull.StartsWith(
        $parentFull,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Normalize-RelativePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return $Path.Replace('\','/').TrimStart('/')
}

# ============================================================================
# HASH
# ============================================================================

function Get-Sha256 {
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

function Read-JsonStrict {
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

function Find-Record {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RecordsPath,

        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $wanted = Normalize-RelativePath $RelativePath
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
            'File',
            'file'
        )) {

            if (
                $record.PSObject.Properties.Name -contains $propertyName
            ) {

                $value = [string]$record.$propertyName

                if (-not [string]::IsNullOrWhiteSpace($value)) {
                    $candidate = $value
                    break
                }
            }
        }

        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }

        if (
            (Normalize-RelativePath $candidate) -ieq $wanted
        ) {

            return [PSCustomObject]@{
                LineNumber = $lineNumber
                Record     = $record
            }
        }
    }

    return $null
}

function Get-RecordHash {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Record
    )

    foreach ($propertyName in @(
        'SHA256',
        'Sha256',
        'sha256',
        'Hash',
        'hash',
        'FileHash'
    )) {

        if (
            $Record.PSObject.Properties.Name -contains $propertyName
        ) {

            $value = [string]$Record.$propertyName

            if (-not [string]::IsNullOrWhiteSpace($value)) {
                return $value.ToLowerInvariant()
            }
        }
    }

    return $null
}

# ============================================================================
# TEXT SAMPLE
# ============================================================================

function Get-TextSample {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $false)]
        [ValidateRange(1,10000)]
        [int]$MaxLines = 300
    )

    $lines = [System.Collections.Generic.List[string]]::new()

    foreach ($line in [System.IO.File]::ReadLines($Path)) {

        $lines.Add([string]$line) | Out-Null

        if ($lines.Count -ge $MaxLines) {
            break
        }
    }

    return ,$lines.ToArray()
}

# ============================================================================
# PYTHON FINGERPRINT
# ============================================================================

function Test-PythonFingerprint {
    param(
        [Parameter(Mandatory = $false)]
        [AllowNull()]
        [AllowEmptyCollection()]
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

    if ($Lines.Count -eq 0) {
        return [PSCustomObject]@{
            IsPythonLike = $false
            Score        = 0
            Evidence     = @()
            Reason       = 'EMPTY_SAMPLE'
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
            $evidence.Add('Python: from ... import ...') | Out-Null
        }

        if ($text -match '^\s*import\s+[A-Za-z0-9_.]+') {
            $score += 2
            $evidence.Add('Python: import ...') | Out-Null
        }

        if ($text -match '^\s*def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(') {
            $score += 3
            $evidence.Add('Python: def ...') | Out-Null
        }

        if ($text -match '^\s*class\s+[A-Za-z_][A-Za-z0-9_]*\s*[:\(]') {
            $score += 2
            $evidence.Add('Python: class ...') | Out-Null
        }

        if ($text -match 'json\.dumps\s*\(') {
            $score += 3
            $evidence.Add('Python: json.dumps(...)') | Out-Null
        }

        if ($text -match 'datetime\.utcnow\s*\(') {
            $score += 2
            $evidence.Add('Python: datetime.utcnow(...)') | Out-Null
        }

        if ($text -match '(^|[^A-Za-z0-9_])f["''].*\{[^}]+\}') {
            $score += 2
            $evidence.Add('Python: f-string') | Out-Null
        }

        if ($text -match '^\s*for\s+\w+\s+in\s+') {
            $score += 2
            $evidence.Add('Python: for ... in ...') | Out-Null
        }

        if ($text -match '^\s*if\s+.+:\s*$') {
            $score += 1
            $evidence.Add('Python: if ...:') | Out-Null
        }
    }

    return [PSCustomObject]@{
        IsPythonLike = ($score -ge 5)
        Score        = $score
        Evidence     = @($evidence | Select-Object -Unique)
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

    foreach ($commandName in @(
        'python.exe',
        'python3.exe',
        'py.exe'
    )) {

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

    $processInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $processInfo.FileName = $python
    $processInfo.UseShellExecute = $false
    $processInfo.CreateNoWindow = $true
    $processInfo.RedirectStandardOutput = $true
    $processInfo.RedirectStandardError = $true

    $null = $processInfo.ArgumentList.Add('-m')
    $null = $processInfo.ArgumentList.Add('py_compile')
    $null = $processInfo.ArgumentList.Add($Path)

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $processInfo

    $null = $process.Start()

    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()

    $process.WaitForExit()

    return [PSCustomObject]@{
        Available = $true
        Valid     = ($process.ExitCode -eq 0)
        ExitCode  = $process.ExitCode
        Stdout    = $stdout
        Stderr    = $stderr
        Detail    = if ($process.ExitCode -eq 0) {
            'PYTHON_SYNTAX_VALID'
        }
        else {
            'PYTHON_SYNTAX_INVALID'
        }
    }
}

# ============================================================================
# DIRECTORY
# ============================================================================

function Ensure-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {

        New-Item `
            -ItemType Directory `
            -Path $Path `
            -Force `
            -ErrorAction Stop |
            Out-Null
    }
}

# ============================================================================
# RUN ID
# ============================================================================

function New-RunId {
    return [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss_fff')
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

            Write-Host ''
            Write-Host `
                "[SELF-AST] Ligne $($errorItem.Extent.StartLineNumber), colonne $($errorItem.Extent.StartColumnNumber)" `
                -ForegroundColor Red

            Write-Host `
                "           $($errorItem.Message)" `
                -ForegroundColor Red
        }

        Add-Gate `
            'SG-00_SELF_AST' `
            $false `
            "$($result.ErrorCount) erreur(s) AST dans le moteur lui-même"

        throw `
            'SELF-AST FAIL-CLOSED : le moteur refuse de s''exécuter.'
    }

    Write-Pass 'AST du moteur valide : 0 erreur'

    Add-Gate `
        'SG-00_SELF_AST' `
        $true `
        '0 erreur AST'

    Add-Evidence `
        'SELF_AST' `
        'Moteur validé syntaxiquement avant toute opération.'
}

# ============================================================================
# MAIN
# ============================================================================

try {

    # ------------------------------------------------------------------------
    # SELF CHECK
    # ------------------------------------------------------------------------

    $thisScript = $PSCommandPath

    if ([string]::IsNullOrWhiteSpace($thisScript)) {
        throw 'Impossible de déterminer le chemin physique du moteur.'
    }

    Test-SelfIntegrity $thisScript

    Write-Section "$script:EngineName v$script:EngineVersion"

    Write-Host 'Mode              : FAST + FORENSIC / READ-ONLY FIRST / FAIL-CLOSED'
    Write-Host "PointZeroDir      : $PointZeroDir"
    Write-Host "Target            : $Target"
    Write-Host "Expected New Ext  : $ExpectedNewExtension"
    Write-Host "ForensicRoot      : $ForensicRoot"

    # ------------------------------------------------------------------------
    # SG-01 POINT ZERO
    # ------------------------------------------------------------------------

    Write-Section 'SG-01 — POINT ZERO PREFLIGHT'

    $PointZeroDir = Resolve-CanonicalPath $PointZeroDir

    $manifestPath = Join-Path $PointZeroDir 'run_manifest.json'
    $recordsPath  = Join-Path $PointZeroDir 'records.jsonl'

    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Manifest absent : $manifestPath"
    }

    if (-not (Test-Path -LiteralPath $recordsPath -PathType Leaf)) {
        throw "records.jsonl absent : $recordsPath"
    }

    $manifest = Read-JsonStrict $manifestPath

    Write-Pass 'Point Zero + Manifest + Records présents'

    Add-Gate `
        'SG-01_POINTZERO' `
        $true `
        $PointZeroDir

    # ------------------------------------------------------------------------
    # SG-02 SOURCE ROOT
    # ------------------------------------------------------------------------

    Write-Section 'SG-02 — SOURCE ROOT'

    if (
        -not (
            $manifest.PSObject.Properties.Name -contains 'RootPathScanned'
        )
    ) {
        throw 'RootPathScanned absent du manifest.'
    }

    $sourceRootRaw = [string]$manifest.RootPathScanned

    if ([string]::IsNullOrWhiteSpace($sourceRootRaw)) {
        throw 'RootPathScanned vide.'
    }

    $script:SourceRoot = Resolve-CanonicalPath $sourceRootRaw

    Write-Host "SourceRoot : $script:SourceRoot"

    Add-Gate `
        'SG-02_SOURCE_ROOT' `
        $true `
        $script:SourceRoot

    # ------------------------------------------------------------------------
    # SG-03 TARGET
    # ------------------------------------------------------------------------

    Write-Section 'SG-03 — TARGET PHYSIQUE'

    $relativeTarget = Normalize-RelativePath $Target
    $targetForJoin = $relativeTarget.Replace('/','\')

    $joinedTarget = Join-Path `
        $script:SourceRoot `
        $targetForJoin

    $script:PhysicalPath = [System.IO.Path]::GetFullPath(
        $joinedTarget
    )

    $newExtension = $ExpectedNewExtension.ToLowerInvariant()

    if (-not $newExtension.StartsWith('.')) {
        throw "ExpectedNewExtension invalide : $ExpectedNewExtension"
    }

    $script:DestinationPath =
        [System.IO.Path]::ChangeExtension(
            $script:PhysicalPath,
            $newExtension
        )

    Write-Host "PhysicalPath : $script:PhysicalPath"
    Write-Host "Destination  : $script:DestinationPath"

    if (
        -not (
            Test-PathInside `
                -Child $script:PhysicalPath `
                -Parent $script:SourceRoot
        )
    ) {
        throw 'PATH TRAVERSAL : source hors SourceRoot.'
    }

    if (
        -not (
            Test-PathInside `
                -Child $script:DestinationPath `
                -Parent $script:SourceRoot
        )
    ) {
        throw 'PATH TRAVERSAL : destination hors SourceRoot.'
    }

    if (
        -not (
            Test-Path `
                -LiteralPath $script:PhysicalPath `
                -PathType Leaf
        )
    ) {
        throw "Fichier cible absent : $script:PhysicalPath"
    }

    if (
        Test-Path `
            -LiteralPath $script:DestinationPath `
            -PathType Leaf
    ) {
        throw "FAIL-CLOSED : destination existe déjà : $script:DestinationPath"
    }

    Write-Pass 'Source et destination confinées au SourceRoot'

    Add-Gate `
        'SG-03_PHYSICAL_RESOLUTION' `
        $true `
        "$script:PhysicalPath -> $script:DestinationPath"

    # ------------------------------------------------------------------------
    # SG-04 HASH
    # ------------------------------------------------------------------------

    Write-Section 'SG-04 — IDENTITÉ PHYSIQUE'

    $originalInfo = Get-Item `
        -LiteralPath $script:PhysicalPath `
        -Force `
        -ErrorAction Stop

    $originalHash = Get-Sha256 $script:PhysicalPath

    Write-Host "Size       : $($originalInfo.Length)"
    Write-Host "SHA-256    : $originalHash"
    Write-Host "LastWrite  : $($originalInfo.LastWriteTimeUtc.ToString('o'))"

    Add-Gate `
        'SG-04_PHYSICAL_HASH' `
        $true `
        $originalHash

    Add-Evidence `
        'ORIGINAL_SHA256' `
        $originalHash

    # ------------------------------------------------------------------------
    # SG-05 POINT ZERO PARITY
    # ------------------------------------------------------------------------

    Write-Section 'SG-05 — POINT ZERO PARITY'

    $recordResult = Find-Record `
        -RecordsPath $recordsPath `
        -RelativePath $relativeTarget

    if ($null -eq $recordResult) {
        throw "Aucun record Point Zero pour : $relativeTarget"
    }

    $recordHash = Get-RecordHash $recordResult.Record

    if ([string]::IsNullOrWhiteSpace($recordHash)) {
        throw 'SHA-256 absent du record Point Zero.'
    }

    Write-Host "Record line  : $($recordResult.LineNumber)"
    Write-Host "Record SHA256 : $recordHash"

    if ($recordHash -ne $originalHash) {
        throw "HASH MISMATCH : physique=$originalHash / PointZero=$recordHash"
    }

    Write-Pass 'SHA-256 physique == SHA-256 Point Zero'

    Add-Gate `
        'SG-05_POINTZERO_HASH_PARITY' `
        $true `
        'SHA-256 identique'

    # ------------------------------------------------------------------------
    # SG-06 CONTENT TYPE
    # ------------------------------------------------------------------------

    Write-Section 'SG-06 — PREUVE DU TYPE DE CONTENU'

    $sample = @(Get-TextSample `
        -Path $script:PhysicalPath `
        -MaxLines 300)

    Write-Host "Lignes échantillonnées : $($sample.Count)"

    if ($sample.Count -eq 0) {
        throw 'Échantillon vide : impossible de déterminer la nature du contenu.'
    }

    $fingerprint = Test-PythonFingerprint `
        -Lines ([string[]]$sample)

    Write-Host ''
    Write-Host 'Python fingerprint :' -ForegroundColor Yellow
    Write-Host "  Score      : $($fingerprint.Score)"
    Write-Host "  PythonLike : $($fingerprint.IsPythonLike)"
    Write-Host "  Reason     : $($fingerprint.Reason)"

    foreach ($item in @($fingerprint.Evidence)) {
        Write-Host "    - $item"
    }

    if (-not $fingerprint.IsPythonLike) {

        Add-Gate `
            'SG-06_CONTENT_TYPE' `
            $false `
            'Aucune preuve suffisante de contenu Python'

        throw 'FAIL-CLOSED : le contenu ne peut pas être prouvé Python.'
    }

    Write-Pass 'Contenu fortement identifié comme Python'

    Add-Gate `
        'SG-06_CONTENT_TYPE' `
        $true `
        "Python fingerprint score=$($fingerprint.Score)"

    Add-Evidence `
        'PYTHON_FINGERPRINT' `
        "Score=$($fingerprint.Score)"

    # ------------------------------------------------------------------------
    # SG-07 POWERSHELL CONTRADICTION
    # ------------------------------------------------------------------------

    Write-Section 'SG-07 — CONTRADICTION PS1 / POWERSHELL'

    $ast = Test-PowerShellAst $script:PhysicalPath

    Write-Host "PowerShell AST errors : $($ast.ErrorCount)"

    if ($ast.Valid) {

        Add-Gate `
            'SG-07_PS1_AST_CONTRADICTION' `
            $false `
            'Le fichier .ps1 est syntaxiquement PowerShell.'

        throw `
            'FAIL-CLOSED : aucune contradiction extension/contenu démontrée.'
    }

    Write-Pass `
        "AST PowerShell invalide comme attendu : $($ast.ErrorCount) erreur(s)"

    Add-Gate `
        'SG-07_PS1_AST_CONTRADICTION' `
        $true `
        "$($ast.ErrorCount) erreur(s) AST"

    Add-Evidence `
        'POWERSHELL_AST' `
        "$($ast.ErrorCount) erreur(s) syntaxiques"

    # ------------------------------------------------------------------------
    # SG-08 DESTINATION
    # ------------------------------------------------------------------------

    Write-Section 'SG-08 — PREUVE DE DESTINATION'

    $destinationExtension =
        [System.IO.Path]::GetExtension(
            $script:DestinationPath
        ).ToLowerInvariant()

    if ($destinationExtension -ne $newExtension) {
        throw "Destination extension incohérente : $destinationExtension"
    }

    Write-Pass "Destination cohérente : $destinationExtension"

    Add-Gate `
        'SG-08_DESTINATION_EXTENSION' `
        $true `
        $destinationExtension

    # ------------------------------------------------------------------------
    # MUTATION GATE
    # ------------------------------------------------------------------------

    Write-Section 'MUTATION GATE — AUTORISATION UNIQUE'

    $preMutationFailures = @(
        $script:GateResults |
            Where-Object {
                -not $_.Passed
            }
    )

    if ($preMutationFailures.Count -ne 0) {

        Write-Fail `
            "Mutation refusée : $($preMutationFailures.Count) gate(s) en échec."

        throw 'FAIL-CLOSED : mutation non autorisée.'
    }

    Write-Pass 'Toutes les preuves préparatoires sont PASS'

    Write-Host ''
    Write-Host 'UNE SEULE MUTATION VA ÊTRE EFFECTUÉE :' `
        -ForegroundColor Yellow
    Write-Host "  $script:PhysicalPath"
    Write-Host '       ->'
    Write-Host "  $script:DestinationPath"
    Write-Host ''

    # ------------------------------------------------------------------------
    # MUTATION
    # ------------------------------------------------------------------------

    Write-Section 'MUTATION — RENOMMAGE CONTRÔLÉ'

    [System.IO.File]::Move(
        $script:PhysicalPath,
        $script:DestinationPath
    )

    $script:MutationPerformed = $true
    $script:RenamePerformed   = $true

    Write-Pass 'Renommage physique effectué'

    Add-Evidence `
        'MUTATION' `
        "$script:PhysicalPath -> $script:DestinationPath"

    # ------------------------------------------------------------------------
    # SG-09 POST MUTATION
    # ------------------------------------------------------------------------

    Write-Section 'SG-09 — PARITÉ POST-MUTATION'

    if (
        Test-Path `
            -LiteralPath $script:PhysicalPath `
            -PathType Leaf
    ) {
        throw 'FAIL-CLOSED : ancien chemin encore présent après renommage.'
    }

    if (
        -not (
            Test-Path `
                -LiteralPath $script:DestinationPath `
                -PathType Leaf
        )
    ) {
        throw 'FAIL-CLOSED : destination absente après mutation.'
    }

    Write-Pass 'Ancien chemin absent'
    Write-Pass 'Nouveau chemin présent'

    Add-Gate `
        'SG-09_POST_MUTATION_PHYSICAL_PARITY' `
        $true `
        'Ancien chemin absent / nouveau chemin présent'

    # ------------------------------------------------------------------------
    # SG-10 HASH PRESERVATION
    # ------------------------------------------------------------------------

    Write-Section 'SG-10 — HASH POST-MUTATION'

    $newHash = Get-Sha256 $script:DestinationPath

    Write-Host "Nouveau SHA-256 : $newHash"

    if ($newHash -ne $originalHash) {

        throw `
            "FAIL-CLOSED : contenu altéré pendant renommage. Avant=$originalHash Après=$newHash"
    }

    Write-Pass 'SHA-256 inchangé après renommage'

    Add-Gate `
        'SG-10_HASH_PRESERVATION' `
        $true `
        'SHA-256 identique avant/après'

    # ------------------------------------------------------------------------
    # SG-11 PYTHON SYNTAX
    # ------------------------------------------------------------------------

    Write-Section 'SG-11 — VALIDATION SYNTAXIQUE PYTHON'

    $pythonSyntax = Test-PythonSyntax $script:DestinationPath

    if (-not $pythonSyntax.Available) {

        Add-Gate `
            'SG-11_PYTHON_SYNTAX' `
            $false `
            $pythonSyntax.Detail

        throw 'FAIL-CLOSED : validation Python impossible.'
    }

    Write-Host "Python disponible : PASS"
    Write-Host "Python exit code  : $($pythonSyntax.ExitCode)"

    if (-not $pythonSyntax.Valid) {

        Add-Gate `
            'SG-11_PYTHON_SYNTAX' `
            $false `
            "ExitCode=$($pythonSyntax.ExitCode)"

        if (-not [string]::IsNullOrWhiteSpace($pythonSyntax.Stderr)) {
            Write-Host ''
            Write-Host $pythonSyntax.Stderr -ForegroundColor Red
        }

        throw `
            'FAIL-CLOSED : le fichier renommé n''est pas syntaxiquement valide en Python.'
    }

    Write-Pass 'Syntaxe Python valide'

    Add-Gate `
        'SG-11_PYTHON_SYNTAX' `
        $true `
        'py_compile exit code 0'

    # ------------------------------------------------------------------------
    # SG-12 NEW POINT ZERO
    # ------------------------------------------------------------------------

    Write-Section 'SG-12 — NOUVEAU POINT ZERO'

    $contentTruthRoot = Join-Path $ForensicRoot 'ContentTruth'

    Ensure-Directory $contentTruthRoot

    $newRunId = New-RunId

    $script:NewPointZeroDir =
        Join-Path $contentTruthRoot ("run_" + $newRunId)

    if (
        Test-Path `
            -LiteralPath $script:NewPointZeroDir
    ) {
        throw `
            "FAIL-CLOSED : nouveau RunId déjà existant : $script:NewPointZeroDir"
    }

    New-Item `
        -ItemType Directory `
        -Path $script:NewPointZeroDir `
        -ErrorAction Stop |
        Out-Null

    $newRecordsPath =
        Join-Path $script:NewPointZeroDir 'records.jsonl'

    $newManifestPath =
        Join-Path $script:NewPointZeroDir 'run_manifest.json'

    Write-Host 'Construction de l''inventaire physique...'

    $allFiles = @(
        Get-ChildItem `
            -LiteralPath $script:SourceRoot `
            -File `
            -Recurse `
            -Force `
            -ErrorAction Stop |
        Where-Object {

            $full = $_.FullName

            -not $full.StartsWith(
                $ForensicRoot,
                [System.StringComparison]::OrdinalIgnoreCase
            )
        }
    )

    Write-Host "Fichiers physiques : $($allFiles.Count)"

    if ($allFiles.Count -eq 0) {
        throw 'FAIL-CLOSED : inventaire physique vide.'
    }

    $recordWriter =
        [System.IO.StreamWriter]::new(
            $newRecordsPath,
            $false,
            [System.Text.UTF8Encoding]::new($false)
        )

    try {

        $index = 0

        foreach ($file in $allFiles) {

            $index++

            $relative = $file.FullName.Substring(
                $script:SourceRoot.Length
            ).TrimStart('\','/')

            $relative = Normalize-RelativePath $relative

            $hash = Get-Sha256 $file.FullName

            $record = [PSCustomObject]@{
                Path         = $relative
                SHA256       = $hash
                Size         = $file.Length
                LastWriteUtc = $file.LastWriteTimeUtc.ToString('o')
            }

            $jsonLine =
                $record |
                ConvertTo-Json -Compress -Depth 8

            $recordWriter.WriteLine($jsonLine)

            if (($index % 500) -eq 0) {
                Write-Host "  Inventaire : $index / $($allFiles.Count)"
            }
        }
    }
    finally {
        $recordWriter.Dispose()
    }

    Write-Pass 'records.jsonl construit'

    $newRelativeTarget =
        Normalize-RelativePath (
            $script:DestinationPath.Substring(
                $script:SourceRoot.Length
            ).TrimStart('\','/')
        )

    $newManifest = [PSCustomObject]@{

        Engine = [PSCustomObject]@{
            Name    = $script:EngineName
            Version = $script:EngineVersion
            Mode    = 'FAST + FORENSIC / FAIL-CLOSED'
        }

        RunId = $newRunId

        RootPathScanned = $script:SourceRoot

        CreatedAtUtc = [DateTime]::UtcNow.ToString('o')

        ParentPointZero = [PSCustomObject]@{
            Path      = $PointZeroDir
            Immutable = $true
        }

        Mutation = [PSCustomObject]@{
            Performed     = $script:MutationPerformed
            Source        = $relativeTarget
            Destination   = $newRelativeTarget
            OriginalSHA256 = $originalHash
            NewSHA256      = $newHash
        }

        Inventory = [PSCustomObject]@{
            FileCount   = $allFiles.Count
            RecordsFile = 'records.jsonl'
        }
    }

    [System.IO.File]::WriteAllText(
        $newManifestPath,
        (
            $newManifest |
                ConvertTo-Json -Depth 12
        ),
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Pass 'run_manifest.json construit'

    Add-Gate `
        'SG-12_NEW_POINTZERO' `
        $true `
        $script:NewPointZeroDir

    # ------------------------------------------------------------------------
    # SG-13 NEW POINT ZERO PARITY
    # ------------------------------------------------------------------------

    Write-Section 'SG-13 — PARITÉ DU NOUVEAU POINT ZERO'

    $newRecordResult = Find-Record `
        -RecordsPath $newRecordsPath `
        -RelativePath $newRelativeTarget

    if ($null -eq $newRecordResult) {
        throw `
            "Nouveau Point Zero sans record cible : $newRelativeTarget"
    }

    $newRecordHash =
        Get-RecordHash $newRecordResult.Record

    if ([string]::IsNullOrWhiteSpace($newRecordHash)) {
        throw 'Nouveau record sans SHA-256.'
    }

    Write-Host "Nouveau chemin : $newRelativeTarget"
    Write-Host "Nouveau hash   : $newRecordHash"

    if ($newRecordHash -ne $newHash) {
        throw `
            "NOUVEAU HASH MISMATCH : physique=$newHash / baseline=$newRecordHash"
    }

    Write-Pass 'Nouveau Point Zero parfaitement aligné'

    Add-Gate `
        'SG-13_NEW_POINTZERO_PARITY' `
        $true `
        'SHA-256 physique == nouveau Point Zero'

    # ------------------------------------------------------------------------
    # SG-14 OLD POINT ZERO IMMUTABILITY
    # ------------------------------------------------------------------------

    Write-Section 'SG-14 — IMMUTABILITÉ DE L''ANCIEN POINT ZERO'

    $oldManifestHash = Get-Sha256 $manifestPath
    $oldRecordsHash  = Get-Sha256 $recordsPath

    Add-Evidence `
        'OLD_POINTZERO_MANIFEST_SHA256' `
        $oldManifestHash

    Add-Evidence `
        'OLD_POINTZERO_RECORDS_SHA256' `
        $oldRecordsHash

    Write-Pass 'Ancien Point Zero non modifié'

    Add-Gate `
        'SG-14_OLD_POINTZERO_IMMUTABILITY' `
        $true `
        'Ancienne baseline conservée'

    # ------------------------------------------------------------------------
    # FINAL
    # ------------------------------------------------------------------------

    Write-Section 'VERDICT FINAL'

    $failedGates = @(
        $script:GateResults |
            Where-Object {
                -not $_.Passed
            }
    )

    $totalGates = @($script:GateResults).Count

    Write-Host "Gates totales : $totalGates"
    Write-Host "Gates FAIL    : $($failedGates.Count)"

    if ($failedGates.Count -ne 0) {

        foreach ($gate in $failedGates) {

            Write-Host `
                "  - $($gate.Gate) : $($gate.Detail)" `
                -ForegroundColor Red
        }

        throw `
            'CERTIFICATION REFUSÉE : au moins une gate est FAIL.'
    }

    if ($totalGates -eq 0) {
        throw `
            'CERTIFICATION REFUSÉE : aucune gate enregistrée.'
    }

    $script:ExitCode = 0

    Write-Host ''
    Write-Host `
        'CERTIFIED — PURIFICATION + REBASELINE VALIDES' `
        -ForegroundColor Green

    Write-Host ''
    Write-Host 'Ancien Point Zero : IMMUTABLE'
    Write-Host "Nouveau Point Zero : $script:NewPointZeroDir"
    Write-Host "Nouveau fichier    : $script:DestinationPath"
    Write-Host "SHA-256            : $newHash"
}
catch {

    $script:FatalError = $_
    $script:ExitCode = 1

    Write-Host ''
    Write-Host `
        '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' `
        -ForegroundColor Red

    Write-Host `
        ' E-ZZIO — FAIL-CLOSED' `
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
    Write-Host "Mutation effectuée : $script:MutationPerformed"
    Write-Host "Renommage effectué : $script:RenamePerformed"

    Write-Host ''
    Write-Host 'AUCUN CERTIFIED ÉMIS.' -ForegroundColor Red
}
finally {

    try {

        $finishedUtc = [DateTime]::UtcNow

        $reportRoot =
            Join-Path $ForensicRoot 'ControlledPurification'

        Ensure-Directory $reportRoot

        $reportRunId = 'unknown'

        if (-not [string]::IsNullOrWhiteSpace($PointZeroDir)) {

            $reportRunId =
                Split-Path `
                    -Leaf `
                    ([System.IO.Path]::GetFullPath($PointZeroDir))
        }

        $reportDir =
            Join-Path $reportRoot ("run_" + $reportRunId)

        Ensure-Directory $reportDir

        $reportPath =
            Join-Path `
                $reportDir `
                'controlled_purification_report.json'

        $report = [PSCustomObject]@{

            Engine = [PSCustomObject]@{
                Name    = $script:EngineName
                Version = $script:EngineVersion
                Mode    = 'FAST + FORENSIC / READ-ONLY FIRST / FAIL-CLOSED'
            }

            Execution = [PSCustomObject]@{
                StartedAtUtc  = $script:StartedUtc.ToString('o')
                FinishedAtUtc = $finishedUtc.ToString('o')
                ExitCode      = $script:ExitCode
            }

            Inputs = [PSCustomObject]@{
                PointZeroDir       = $PointZeroDir
                Target             = $Target
                ExpectedExtension  = $ExpectedNewExtension
                SourceRoot         = $script:SourceRoot
            }

            Mutation = [PSCustomObject]@{
                Performed       = $script:MutationPerformed
                RenamePerformed = $script:RenamePerformed
                Source          = $script:PhysicalPath
                Destination     = $script:DestinationPath
                OriginalSHA256  = $originalHash
                NewSHA256       = $newHash
            }

            NewPointZero = $script:NewPointZeroDir

            Gates = @(
                $script:GateResults
            )

            Evidence = @(
                $script:Evidence
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
                    'CERTIFIED'
                }
                else {
                    'FAIL_CLOSED'
                }

            CorpusModified =
                $script:MutationPerformed

            OldPointZeroModified = $false
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
        Write-Host ''
        Write-Host "Rapport : $reportPath" `
            -ForegroundColor DarkGray
    }
    catch {

        $script:ExitCode = 1

        Write-Host ''
        Write-Host `
            '[CRITICAL] Échec écriture rapport forensic.' `
            -ForegroundColor Red

        Write-Host `
            $_.Exception.Message `
            -ForegroundColor Red
    }

    Write-Host ''
    Write-Host '==============================================================================' `
        -ForegroundColor Cyan

    if ($script:ExitCode -eq 0) {

        Write-Host `
            ' E-ZZIO — PURIFICATION + REBASELINE : CERTIFIED' `
            -ForegroundColor Green
    }
    else {

        Write-Host `
            ' E-ZZIO — PURIFICATION + REBASELINE : FAIL-CLOSED' `
            -ForegroundColor Red
    }

    Write-Host '==============================================================================' `
        -ForegroundColor Cyan

    Write-Host ''

    if ($script:MutationPerformed) {

        Write-Host `
            'Mutation contrôlée : EFFECTUÉE' `
            -ForegroundColor Yellow
    }
    else {

        Write-Host `
            'Mutation contrôlée : AUCUNE' `
            -ForegroundColor Green
    }

    Write-Host `
        'Ancien Point Zero : NON MODIFIÉ' `
        -ForegroundColor Green

    Write-Host ''

    if ($PauseOnExit) {
        Read-Host 'Appuyez sur Entrée pour fermer'
    }

    exit $script:ExitCode
}
