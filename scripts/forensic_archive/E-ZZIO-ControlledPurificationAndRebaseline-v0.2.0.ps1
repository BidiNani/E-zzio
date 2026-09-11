# ============================================================================
# E-ZZIO — CONTROLLED PURIFICATION + REBASELINE v0.2.0
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
    [string]$ExpectedNewExtension = '.py',

    [Parameter(Mandatory = $false)]
    [string]$ForensicRoot = 'G:\AI\_forensic',

    [Parameter(Mandatory = $false)]
    [switch]$PauseOnExit
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:EngineVersion = '0.2.0'
$script:ExitCode = 1
$script:FatalError = $null
$script:MutationPerformed = $false
$script:GateResults = [System.Collections.Generic.List[object]]::new()
$script:Warnings = [System.Collections.Generic.List[string]]::new()
$script:StartUtc = [DateTime]::UtcNow

$sourceRoot = $null
$physicalPath = $null
$destinationPath = $null
$newPointZeroDir = $null

function Write-Section {
    param([Parameter(Mandatory)][string]$Title)

    Write-Host ''
    Write-Host '==============================================================================' -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host '==============================================================================' -ForegroundColor Cyan
}

function Write-Pass {
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "[PASS] $Message" -ForegroundColor Green
}

function Write-Fail {
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Write-Warn {
    param([Parameter(Mandatory)][string]$Message)

    $script:Warnings.Add($Message) | Out-Null
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Add-GateResult {
    param(
        [Parameter(Mandatory)][string]$Gate,
        [Parameter(Mandatory)][bool]$Passed,
        [Parameter(Mandatory)][string]$Detail
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

function Resolve-CanonicalPath {
    param([Parameter(Mandatory)][string]$Path)

    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction Stop

    return [System.IO.Path]::GetFullPath($resolved.Path)
}

function Test-PathInside {
    param(
        [Parameter(Mandatory)][string]$Child,
        [Parameter(Mandatory)][string]$Parent
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

function Get-FileSha256 {
    param([Parameter(Mandatory)][string]$Path)

    return (
        Get-FileHash `
            -LiteralPath $Path `
            -Algorithm SHA256 `
            -ErrorAction Stop
    ).Hash.ToLowerInvariant()
}

function Read-JsonFileStrict {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "JSON introuvable : $Path"
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

function Get-ObjectPropertyValue {
    param(
        [Parameter(Mandatory)][object]$Object,
        [Parameter(Mandatory)][string[]]$Names
    )

    foreach ($name in $Names) {
        if ($Object.PSObject.Properties.Name -contains $name) {
            $value = $Object.$name

            if ($null -ne $value) {
                $text = [string]$value

                if (-not [string]::IsNullOrWhiteSpace($text)) {
                    return $value
                }
            }
        }
    }

    return $null
}

function Find-RecordForRelativePath {
    param(
        [Parameter(Mandatory)][string]$RecordsPath,
        [Parameter(Mandatory)][string]$RelativePath
    )

    $normalizedTarget =
        $RelativePath.Replace('\','/').TrimStart('/')

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

        $candidate = Get-ObjectPropertyValue `
            -Object $record `
            -Names @(
                'Path',
                'RelativePath',
                'relPath',
                'relative_path',
                'File'
            )

        if ($null -eq $candidate) {
            continue
        }

        $candidateNormalized =
            ([string]$candidate).Replace('\','/').TrimStart('/')

        if ($candidateNormalized -ieq $normalizedTarget) {

            return [PSCustomObject]@{
                LineNumber = $lineNumber
                Record     = $record
            }
        }
    }

    return $null
}

function Get-SafeTextSample {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][int]$MaxLines = 300
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Fichier absent : $Path"
    }

    $lines = [System.Collections.Generic.List[string]]::new()

    foreach ($line in [System.IO.File]::ReadLines($Path)) {

        $lines.Add([string]$line)

        if ($lines.Count -ge $MaxLines) {
            break
        }
    }

    # IMPORTANT:
    # Une liste PowerShell contenant un seul élément peut être déroulée
    # en chaîne. On force donc explicitement un tableau typé.
    if ($lines.Count -eq 0) {
        return [string[]]@()
    }

    return [string[]]$lines.ToArray()
}

function Test-PythonFingerprint {
    param(
        [Parameter(Mandatory)]
        [AllowEmptyCollection()]
        [AllowEmptyString()]
        [string[]]$Lines
    )

    if ($null -eq $Lines) {
        $Lines = [string[]]@()
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

function Test-PowerShellAst {
    param([Parameter(Mandatory)][string]$Path)

    $tokens = $null
    $errors = $null

    $null =
        [System.Management.Automation.Language.Parser]::ParseFile(
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

function Test-PythonSyntax {
    param([Parameter(Mandatory)][string]$Path)

    $python = Get-Command python.exe -ErrorAction SilentlyContinue

    if ($null -eq $python) {
        return [PSCustomObject]@{
            Available = $false
            Valid     = $false
            ExitCode  = $null
            Error     = 'python.exe introuvable'
        }
    }

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $python.Source
    $psi.ArgumentList.Add('-m')
    $psi.ArgumentList.Add('py_compile')
    $psi.ArgumentList.Add($Path)
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $psi

    $null = $process.Start()

    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()

    $process.WaitForExit()

    return [PSCustomObject]@{
        Available = $true
        Valid     = ($process.ExitCode -eq 0)
        ExitCode  = $process.ExitCode
        Output    = $stdout
        Error     = $stderr
    }
}

function Initialize-Dir {
    param([Parameter(Mandatory)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        New-Item `
            -ItemType Directory `
            -Path $Path `
            -Force `
            -ErrorAction Stop | Out-Null
    }
}

function Write-JsonStrict {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][object]$Object
    )

    $json = $Object | ConvertTo-Json -Depth 20

    [System.IO.File]::WriteAllText(
        $Path,
        $json,
        [System.Text.UTF8Encoding]::new($false)
    )
}

try {

    Write-Section "E-ZZIO — CONTROLLED PURIFICATION + REBASELINE v$($script:EngineVersion)"

    Write-Host "Mode              : FORENSIC / FAIL-CLOSED / CONTROLLED"
    Write-Host "PointZeroDir      : $PointZeroDir"
    Write-Host "Target            : $Target"
    Write-Host "Expected New Ext  : $ExpectedNewExtension"
    Write-Host "ForensicRoot      : $ForensicRoot"

    # ========================================================================
    # SG-00
    # ========================================================================

    Write-Section "SG-00 — PREFLIGHT"

    if (-not (Test-Path -LiteralPath $PointZeroDir -PathType Container)) {
        throw "Point Zero inexistant : $PointZeroDir"
    }

    $manifestPath = Join-Path $PointZeroDir 'run_manifest.json'
    $recordsPath  = Join-Path $PointZeroDir 'records.jsonl'

    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "Manifest absent : $manifestPath"
    }

    if (-not (Test-Path -LiteralPath $recordsPath -PathType Leaf)) {
        throw "Records absents : $recordsPath"
    }

    Write-Pass "Point Zero + Manifest + Records présents"

    Add-GateResult 'SG-00_PREFLIGHT' $true 'Point Zero complet'

    # ========================================================================
    # SG-01
    # ========================================================================

    Write-Section "SG-01 — SOURCE ROOT"

    $manifest = Read-JsonFileStrict $manifestPath

    $sourceRootRaw = Get-ObjectPropertyValue `
        -Object $manifest `
        -Names @('RootPathScanned')

    if ($null -eq $sourceRootRaw) {
        throw 'RootPathScanned absent.'
    }

    $sourceRoot = Resolve-CanonicalPath ([string]$sourceRootRaw)

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

    $joinedPath = Join-Path -Path $sourceRoot -ChildPath $targetNormalized
        $physicalPath = [System.IO.Path]::GetFullPath($joinedPath)

    $baseName =
        [System.IO.Path]::GetFileNameWithoutExtension($physicalPath)

    $directory =
        [System.IO.Path]::GetDirectoryName($physicalPath)

    $destinationPath =
        Join-Path $directory ($baseName + $ExpectedNewExtension)

    Write-Host "PhysicalPath : $physicalPath"
    Write-Host "Destination  : $destinationPath"

    if (-not (Test-PathInside $physicalPath $sourceRoot)) {
        throw 'PATH TRAVERSAL source.'
    }

    if (-not (Test-PathInside $destinationPath $sourceRoot)) {
        throw 'PATH TRAVERSAL destination.'
    }

    if (-not (Test-Path -LiteralPath $physicalPath -PathType Leaf)) {
        throw "Fichier source absent : $physicalPath"
    }

    if (Test-Path -LiteralPath $destinationPath) {
        throw "Destination déjà existante : $destinationPath"
    }

    Write-Pass "Source et destination confinées au SourceRoot"
    Write-Pass "Destination absente — aucune collision"

    Add-GateResult `
        'SG-02_PHYSICAL_RESOLUTION' `
        $true `
        'Source et destination valides'

    # ========================================================================
    # SG-03
    # ========================================================================

    Write-Section "SG-03 — IDENTITÉ PHYSIQUE"

    $sourceInfo = Get-Item `
        -LiteralPath $physicalPath `
        -Force `
        -ErrorAction Stop

    $sourceHash = Get-FileSha256 $physicalPath

    Write-Host "Size       : $($sourceInfo.Length) octets"
    Write-Host "SHA-256    : $sourceHash"
    Write-Host "LastWrite  : $($sourceInfo.LastWriteTimeUtc.ToString('o'))"

    Add-GateResult `
        'SG-03_SOURCE_HASH' `
        $true `
        $sourceHash

    # ========================================================================
    # SG-04
    # ========================================================================

    Write-Section "SG-04 — PARITÉ POINT ZERO"

    $recordResult =
        Find-RecordForRelativePath `
            -RecordsPath $recordsPath `
            -RelativePath $targetNormalized

    if ($null -eq $recordResult) {
        throw "Record introuvable : $targetNormalized"
    }

    Write-Pass "Record trouvé à la ligne $($recordResult.LineNumber)"

    $recordHash = Get-ObjectPropertyValue `
        -Object $recordResult.Record `
        -Names @(
            'SHA256',
            'Sha256',
            'sha256',
            'Hash',
            'hash',
            'FileHash'
        )

    if ($null -eq $recordHash) {
        throw 'SHA-256 absent du record.'
    }

    $recordHash = ([string]$recordHash).ToLowerInvariant()

    Write-Host "SHA-256 Point Zero : $recordHash"

    if ($sourceHash -ne $recordHash) {
        throw "HASH MISMATCH : source=$sourceHash / PointZero=$recordHash"
    }

    Write-Pass "SHA-256 physique == Point Zero"

    Add-GateResult `
        'SG-04_POINTZERO_PARITY' `
        $true `
        'SHA-256 identique'

    # ========================================================================
    # SG-05
    # ========================================================================

    Write-Section "SG-05 — PREUVE DU TYPE DE CONTENU"

    $sample = Get-SafeTextSample `
        -Path $physicalPath `
        -MaxLines 300

    $sampleArray = [string[]]$sample

    Write-Host "Lignes échantillonnées : $($sampleArray.Count)"

    if ($sampleArray.Count -eq 0) {
        throw 'Échantillon vide.'
    }

    $fingerprint =
        Test-PythonFingerprint -Lines $sampleArray

    Write-Host "Python Score : $($fingerprint.Score)"
    Write-Host "PythonLike  : $($fingerprint.IsPythonLike)"
    Write-Host "Reason      : $($fingerprint.Reason)"

    foreach ($item in @($fingerprint.Evidence)) {
        Write-Host "  - $item"
    }

    if (-not $fingerprint.IsPythonLike) {
        throw 'Le contenu ne possède pas une preuve Python suffisante.'
    }

    Write-Pass "Preuve forte : contenu Python"

    Add-GateResult `
        'SG-05_CONTENT_TYPE' `
        $true `
        "Python fingerprint score=$($fingerprint.Score)"

    # ========================================================================
    # SG-06
    # ========================================================================

    Write-Section "SG-06 — AST POWERSHELL : PREUVE DE L'ABERRATION"

    $ast = Test-PowerShellAst $physicalPath

    Write-Host "AST Errors : $($ast.ErrorCount)"

    if ($ast.Valid) {
        throw 'Contradiction : fichier PythonLike mais AST PowerShell valide.'
    }

    if ($ast.ErrorCount -le 0) {
        throw 'AST invalide attendu mais aucun diagnostic retourné.'
    }

    Write-Pass "AST PowerShell invalide : aberration confirmée"

    Add-GateResult `
        'SG-06_POWERSHELL_AST' `
        $true `
        "$($ast.ErrorCount) erreurs AST confirmant incompatibilité"

    # ========================================================================
    # SG-07
    # ========================================================================

    Write-Section "SG-07 — PRÉ-CONDITION DE MUTATION"

    Write-Pass 'Ancien Point Zero intact'
    Write-Pass 'Source présente'
    Write-Pass 'Destination absente'
    Write-Pass 'SHA-256 source conforme'
    Write-Pass 'Contenu fortement identifié comme Python'
    Write-Pass 'AST PowerShell invalide'

    Add-GateResult `
        'SG-07_MUTATION_PRECONDITION' `
        $true `
        'Toutes les preuves pré-mutation PASS'

    # ========================================================================
    # MUTATION CONTRÔLÉE
    # ========================================================================

    Write-Section "MUTATION CONTRÔLÉE"

    Write-Host ''
    Write-Host 'ATTENTION : une seule mutation va être effectuée.' -ForegroundColor Yellow
    Write-Host "SOURCE      : $physicalPath"
    Write-Host "DESTINATION : $destinationPath"
    Write-Host ''

    Move-Item `
        -LiteralPath $physicalPath `
        -Destination $destinationPath `
        -Force:$false `
        -ErrorAction Stop

    $script:MutationPerformed = $true

    Write-Pass 'Renommage physique effectué.'

    Add-GateResult `
        'MUTATION_RENAME' `
        $true `
        "$physicalPath -> $destinationPath"

    # ========================================================================
    # SG-08
    # ========================================================================

    Write-Section "SG-08 — VÉRIFICATION POST-MUTATION"

    if (Test-Path -LiteralPath $physicalPath) {
        throw 'Ancien fichier toujours présent après renommage.'
    }

    if (-not (Test-Path -LiteralPath $destinationPath -PathType Leaf)) {
        throw 'Nouveau fichier absent après renommage.'
    }

    $newHash = Get-FileSha256 $destinationPath

    Write-Host "Nouveau SHA-256 : $newHash"

    if ($newHash -ne $sourceHash) {
        throw "HASH POST-MUTATION DIFFÉRENT : avant=$sourceHash après=$newHash"
    }

    Write-Pass 'Ancien chemin absent'
    Write-Pass 'Nouveau chemin présent'
    Write-Pass 'SHA-256 conservé exactement'

    Add-GateResult `
        'SG-08_POST_MUTATION_PARITY' `
        $true `
        "SHA-256 conservé : $newHash"

    # ========================================================================
    # SG-09
    # ========================================================================

    Write-Section "SG-09 — PYTHON SYNTAX FORENSIC"

    $pythonSyntax =
        Test-PythonSyntax -Path $destinationPath

    if (-not $pythonSyntax.Available) {
        throw 'Impossible de certifier Python : python.exe indisponible.'
    }

    Write-Host "Python disponible : $($pythonSyntax.Available)"
    Write-Host "Python exit code   : $($pythonSyntax.ExitCode)"

    if (-not $pythonSyntax.Valid) {

        Write-Host $pythonSyntax.Error -ForegroundColor Red

        throw 'Le fichier renommé .py échoue à py_compile.'
    }

    Write-Pass 'Python py_compile PASS'

    Add-GateResult `
        'SG-09_PYTHON_SYNTAX' `
        $true `
        'py_compile exit code 0'

    # ========================================================================
    # SG-10
    # ========================================================================

    Write-Section "SG-10 — NOUVEAU POINT ZERO"

    $newRunId =
        'run_' +
        [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss_fff')

    $newPointZeroDir =
        Join-Path `
            $ForensicRoot `
            ("ContentTruth\" + $newRunId)

    Initialize-Dir $newPointZeroDir

    $newManifestPath =
        Join-Path $newPointZeroDir 'run_manifest.json'

    $newRecordsPath =
        Join-Path $newPointZeroDir 'records.jsonl'

    $newInventoryPath =
        Join-Path $newPointZeroDir 'inventory.json'

    $newManifest = [PSCustomObject]@{
        Engine            = 'E-ZZIO Controlled Purification + Rebaseline'
        EngineVersion     = $script:EngineVersion
        RunId             = $newRunId
        CreatedAtUtc      = [DateTime]::UtcNow.ToString('o')
        RootPathScanned   = $sourceRoot
        Mode              = 'FORENSIC / FAIL-CLOSED'
        ParentPointZero   = $PointZeroDir
        MutationPerformed = $true
    }

    Write-JsonStrict `
        -Path $newManifestPath `
        -Object $newManifest

    $recordObject = [PSCustomObject]@{
        Path          = $Target.Replace('\','/').TrimStart('/')
        RelativePath  = $Target.Replace('\','/').TrimStart('/')
        SHA256        = $newHash
        Size          = (Get-Item -LiteralPath $destinationPath).Length
        Extension     = $ExpectedNewExtension
        CapturedAtUtc = [DateTime]::UtcNow.ToString('o')
    }

    [System.IO.File]::WriteAllText(
        $newRecordsPath,
        ($recordObject | ConvertTo-Json -Compress -Depth 10),
        [System.Text.UTF8Encoding]::new($false)
    )

    $inventory = [PSCustomObject]@{
        RunId       = $newRunId
        SourceRoot  = $sourceRoot
        Files       = @(
            [PSCustomObject]@{
                Path     = $recordObject.Path
                SHA256   = $recordObject.SHA256
                Size     = $recordObject.Size
                Extension = $recordObject.Extension
            }
        )
    }

    Write-JsonStrict `
        -Path $newInventoryPath `
        -Object $inventory

    if (-not (Test-Path -LiteralPath $newManifestPath -PathType Leaf)) {
        throw 'Nouveau manifest absent.'
    }

    if (-not (Test-Path -LiteralPath $newRecordsPath -PathType Leaf)) {
        throw 'Nouveaux records absents.'
    }

    Write-Pass "Nouveau Point Zero : $newPointZeroDir"

    Add-GateResult `
        'SG-10_NEW_POINTZERO' `
        $true `
        $newPointZeroDir

    # ========================================================================
    # SG-11
    # ========================================================================

    Write-Section "SG-11 — REVALIDATION DU NOUVEAU CORPUS"

    $finalSample =
        [string[]](Get-SafeTextSample `
            -Path $destinationPath `
            -MaxLines 300)

    if ($finalSample.Count -eq 0) {
        throw 'Échantillon final vide.'
    }

    $finalFingerprint =
        Test-PythonFingerprint -Lines $finalSample

    if (-not $finalFingerprint.IsPythonLike) {
        throw 'Fingerprint Python perdu après rebaseline.'
    }

    $finalPython =
        Test-PythonSyntax -Path $destinationPath

    if (-not $finalPython.Available) {
        throw 'Python indisponible lors de la validation finale.'
    }

    if (-not $finalPython.Valid) {
        throw 'Syntaxe Python finale invalide.'
    }

    $finalHash =
        Get-FileSha256 $destinationPath

    if ($finalHash -ne $newHash) {
        throw 'Hash final différent du hash post-mutation.'
    }

    Write-Pass 'Fingerprint Python final PASS'
    Write-Pass 'Python syntax final PASS'
    Write-Pass 'SHA-256 final stable'

    Add-GateResult `
        'SG-11_FINAL_REVALIDATION' `
        $true `
        'Fingerprint + syntaxe + hash conformes'

    # ========================================================================
    # VERDICT
    # ========================================================================

    Write-Section "VERDICT"

    $failedGates = @(
        $script:GateResults |
            Where-Object { -not $_.Passed }
    )

    if ($failedGates.Count -gt 0) {
        throw "Quality Gate finale non nulle : $($failedGates.Count) échec(s)."
    }

    $script:ExitCode = 0

    Write-Host ''
    Write-Host '*****************************************************************************' -ForegroundColor Green
    Write-Host ' E-ZZIO — CERTIFIED' -ForegroundColor Green
    Write-Host '*****************************************************************************' -ForegroundColor Green
    Write-Host ''
    Write-Host 'PURIFICATION       : PASS'
    Write-Host 'NOUVEAU POINT ZERO : PASS'
    Write-Host 'PYTHON SYNTAX      : PASS'
    Write-Host 'HASH PARITY        : PASS'
    Write-Host 'FAILURES           : 0'
    Write-Host ''
    Write-Host "Nouveau fichier : $destinationPath" -ForegroundColor Green
    Write-Host "Nouveau Point Zero : $newPointZeroDir" -ForegroundColor Green
}
catch {

    $script:FatalError = $_
    $script:ExitCode = 1

    Write-Host ''
    Write-Host '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' -ForegroundColor Red
    Write-Host ' E-ZZIO — FAIL-CLOSED' -ForegroundColor Red
    Write-Host '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' -ForegroundColor Red
    Write-Host ''

    Write-Host "ERROR : $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "TYPE  : $($_.Exception.GetType().FullName)" -ForegroundColor Red

    if ($_.InvocationInfo) {
        Write-Host ''
        Write-Host 'FORENSIC LOCATION' -ForegroundColor Yellow
        Write-Host "Script : $($_.InvocationInfo.ScriptName)"
        Write-Host "Line   : $($_.InvocationInfo.ScriptLineNumber)"
        Write-Host "Code   : $($_.InvocationInfo.Line)"
    }

    Write-Host ''

    if ($script:MutationPerformed) {
        Write-Host 'ATTENTION : mutation physique effectuée avant l''échec final.' -ForegroundColor Yellow
        Write-Host 'Le corpus NE DOIT PAS être restauré automatiquement.' -ForegroundColor Yellow
    }
    else {
        Write-Host 'AUCUNE MUTATION PHYSIQUE EFFECTUÉE.' -ForegroundColor Green
    }
}
finally {

    try {

        Initialize-Dir $ForensicRoot

        $reportDir =
            Join-Path `
                $ForensicRoot `
                'ControlledPurification'

        Initialize-Dir $reportDir

        $timestamp =
            [DateTime]::UtcNow.ToString('yyyyMMdd_HHmmss_fff')

        $reportPath =
            Join-Path `
                $reportDir `
                ("purification_rebaseline_" + $timestamp + '.json')

        $report = [PSCustomObject]@{
            Engine = [PSCustomObject]@{
                Name    = 'E-ZZIO — CONTROLLED PURIFICATION + REBASELINE'
                Version = $script:EngineVersion
                Mode    = 'FORENSIC / FAIL-CLOSED / CONTROLLED'
            }

            Execution = [PSCustomObject]@{
                StartedAtUtc  = $script:StartUtc.ToString('o')
                FinishedAtUtc = [DateTime]::UtcNow.ToString('o')
                ExitCode      = $script:ExitCode
            }

            Inputs = [PSCustomObject]@{
                PointZeroDir = $PointZeroDir
                Target       = $Target
                ExpectedNewExtension = $ExpectedNewExtension
                SourceRoot   = $sourceRoot
                PhysicalPath = $physicalPath
                Destination  = $destinationPath
            }

            Mutation = [PSCustomObject]@{
                Performed       = $script:MutationPerformed
                OldPathRemoved  = if ($physicalPath) {
                    -not (Test-Path -LiteralPath $physicalPath)
                } else {
                    $false
                }
                NewPathPresent  = if ($destinationPath) {
                    Test-Path -LiteralPath $destinationPath -PathType Leaf
                } else {
                    $false
                }
            }

            NewPointZero = $newPointZeroDir

            Gates = @(
                $script:GateResults
            )

            Warnings = @(
                $script:Warnings
            )

            FatalError = if ($null -ne $script:FatalError) {
                [PSCustomObject]@{
                    Type    = $script:FatalError.Exception.GetType().FullName
                    Message = $script:FatalError.Exception.Message
                }
            }
            else {
                $null
            }

            Verdict = if ($script:ExitCode -eq 0) {
                'CERTIFIED'
            }
            else {
                'FAIL_CLOSED'
            }
        }

        Write-JsonStrict `
            -Path $reportPath `
            -Object $report

        Write-Host ''
        Write-Host '==============================================================================' -ForegroundColor DarkCyan
        Write-Host ' FORENSIC REPORT' -ForegroundColor DarkCyan
        Write-Host '==============================================================================' -ForegroundColor DarkCyan
        Write-Host "Rapport : $reportPath" -ForegroundColor DarkGray

    }
    catch {

        $script:ExitCode = 1

        Write-Host ''
        Write-Host '[CRITICAL] Impossible d''écrire le rapport forensic.' -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
    }

    Write-Host ''
    Write-Host '==============================================================================' -ForegroundColor Cyan

    if ($script:ExitCode -eq 0) {
        Write-Host ' E-ZZIO — PURIFICATION + REBASELINE : CERTIFIED' -ForegroundColor Green
    }
    else {
        Write-Host ' E-ZZIO — PURIFICATION + REBASELINE : FAIL-CLOSED' -ForegroundColor Red
    }

    Write-Host '==============================================================================' -ForegroundColor Cyan
    Write-Host ''

    if ($script:MutationPerformed) {
        Write-Host 'Mutation : EFFECTUÉE ET JOURNALISÉE.' -ForegroundColor Yellow
    }
    else {
        Write-Host 'Mutation : AUCUNE.' -ForegroundColor Green
    }

    Write-Host 'Ancien Point Zero : NON MODIFIÉ.' -ForegroundColor Green
    Write-Host ''

    if ($PauseOnExit) {
        Read-Host 'Appuyez sur Entrée pour fermer'
    }
}

exit $script:ExitCode
