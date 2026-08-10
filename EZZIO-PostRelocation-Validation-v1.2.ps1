# ==============================================================================
# E-ZZIO POST-RELOCATION VALIDATION ENGINE v1.2
# READ ONLY / HARDENED VALIDATION
# PowerShell 7.x
#
# OBJECTIF :
#   Valider l'état post-relocalisation sans aucune modification.
#
# GARANTIES :
#   - Aucun déplacement
#   - Aucune suppression
#   - Aucun écrasement
#   - Aucune création dans le projet
#   - Aucun nettoyage
#   - Aucun changement d'environnement
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ------------------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------------------

$ProjectRoot = 'G:\AI\E-zzio'
$UserRoot    = $env:USERPROFILE

$AuditRoot = Join-Path $ProjectRoot 'runtime\audit\post-relocation'

$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$RunRoot   = Join-Path $AuditRoot $Timestamp

# ------------------------------------------------------------------------------
# ETAT
# ------------------------------------------------------------------------------

$Failures = [System.Collections.Generic.List[string]]::new()
$Warnings = [System.Collections.Generic.List[string]]::new()
$Passes   = [System.Collections.Generic.List[string]]::new()

# ------------------------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------------------------

function Write-Section {
    param(
        [Parameter(Mandatory)]
        [string]$Title
    )

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan
}

function Add-Pass {
    param(
        [Parameter(Mandatory)]
        [string]$Label,

        [Parameter(Mandatory)]
        [string]$Detail
    )

    $Message = "$Label | $Detail"
    $Passes.Add($Message)
    Write-Host "[OK]   $Message" -ForegroundColor Green
}

function Add-Fail {
    param(
        [Parameter(Mandatory)]
        [string]$Label,

        [Parameter(Mandatory)]
        [string]$Detail
    )

    $Message = "$Label | $Detail"
    $Failures.Add($Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Add-Warn {
    param(
        [Parameter(Mandatory)]
        [string]$Label,

        [Parameter(Mandatory)]
        [string]$Detail
    )

    $Message = "$Label | $Detail"
    $Warnings.Add($Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Test-Directory {
    param(
        [Parameter(Mandatory)]
        [string]$Label,

        [Parameter(Mandatory)]
        [string]$Path
    )

    try {
        if (Test-Path -LiteralPath $Path -PathType Container) {
            Add-Pass $Label $Path
            return $true
        }

        Add-Fail $Label "Répertoire absent : $Path"
        return $false
    }
    catch {
        Add-Fail $Label "$Path | $($_.Exception.Message)"
        return $false
    }
}

function Test-File {
    param(
        [Parameter(Mandatory)]
        [string]$Label,

        [Parameter(Mandatory)]
        [string]$Path
    )

    try {
        if (Test-Path -LiteralPath $Path -PathType Leaf) {
            Add-Pass $Label $Path
            return $true
        }

        Add-Fail $Label "Fichier absent : $Path"
        return $false
    }
    catch {
        Add-Fail $Label "$Path | $($_.Exception.Message)"
        return $false
    }
}

# ------------------------------------------------------------------------------
# DEMARRAGE
# ------------------------------------------------------------------------------

try {

    Write-Section 'E-ZZIO POST-RELOCATION VALIDATION ENGINE v1.2'

    Write-Host "[INFO] PROJECT ROOT = $ProjectRoot"
    Write-Host "[INFO] USER ROOT    = $UserRoot"
    Write-Host '[INFO] MODE         = READ ONLY'
    Write-Host '[INFO] Aucun fichier ne sera modifié.'

    # --------------------------------------------------------------------------
    # 01 — SECURITE
    # --------------------------------------------------------------------------

    Write-Section '01 — GARANTIES DE SECURITE'

    Add-Pass 'READ ONLY' 'Aucune opération destructive ou modificatrice.'
    Add-Pass 'PROJECT ROOT' 'Validation externe au mécanisme de relocalisation.'

    # --------------------------------------------------------------------------
    # 02 — ROOT
    # --------------------------------------------------------------------------

    Write-Section '02 — RACINES'

    if (-not (Test-Directory 'PROJECT ROOT' $ProjectRoot)) {
        throw "PROJECT ROOT inaccessible : $ProjectRoot"
    }

    if (-not (Test-Directory 'USER ROOT' $UserRoot)) {
        throw "USER ROOT inaccessible : $UserRoot"
    }

    # --------------------------------------------------------------------------
    # 03 — STRUCTURE
    # --------------------------------------------------------------------------

    Write-Section '03 — STRUCTURE DU PROJET'

    $DestinationPaths = @(
        @{
            Label = 'DESTINATION PYTHON'
            Path  = Join-Path $ProjectRoot 'runtime\python'
        },
        @{
            Label = 'DESTINATION CACHE'
            Path  = Join-Path $ProjectRoot 'runtime\cache'
        },
        @{
            Label = 'DESTINATION TEMP'
            Path  = Join-Path $ProjectRoot 'runtime\temp'
        },
        @{
            Label = 'DESTINATION EXTERNAL'
            Path  = Join-Path $ProjectRoot 'runtime\external\ezzio'
        },
        @{
            Label = 'DESTINATION TOOLS'
            Path  = Join-Path $ProjectRoot 'runtime\tools'
        },
        @{
            Label = 'DESTINATION DATA'
            Path  = Join-Path $ProjectRoot 'runtime\data'
        },
        @{
            Label = 'DESTINATION AUDIT'
            Path  = Join-Path $ProjectRoot 'runtime\audit'
        }
    )

    foreach ($Destination in $DestinationPaths) {
        Test-Directory $Destination.Label $Destination.Path | Out-Null
    }

    # --------------------------------------------------------------------------
    # 04 — ENVIRONNEMENT
    # --------------------------------------------------------------------------

    Write-Section '04 — ENVIRONNEMENT PYTHON'

    $ExpectedEnvironment = @(
        @{
            Name     = 'EZZIO_TEMP'
            Expected = Join-Path $ProjectRoot 'runtime\temp'
        },
        @{
            Name     = 'PYTHONPYCACHEPREFIX'
            Expected = Join-Path $ProjectRoot 'runtime\cache\pycache'
        },
        @{
            Name     = 'PIP_CACHE_DIR'
            Expected = Join-Path $ProjectRoot 'runtime\cache\pip'
        }
    )

    foreach ($Environment in $ExpectedEnvironment) {

        $Actual = [Environment]::GetEnvironmentVariable(
            $Environment.Name,
            'Process'
        )

        if ([string]::IsNullOrWhiteSpace($Actual)) {
            Add-Fail 'ENV' "$($Environment.Name) | variable absente"
            continue
        }

        if ($Actual.TrimEnd('\') -ieq $Environment.Expected.TrimEnd('\')) {
            Add-Pass "ENV $($Environment.Name)" $Actual
        }
        else {
            Add-Fail 'ENV' "$($Environment.Name) | attendu=$($Environment.Expected) | actuel=$Actual"
        }
    }

    # --------------------------------------------------------------------------
    # 05 — ZONES PYTHON
    # --------------------------------------------------------------------------

    Write-Section '05 — ZONES PYTHON'

    $PythonZonePaths = @(
        (Join-Path $ProjectRoot 'runtime\cache\pycache'),
        (Join-Path $ProjectRoot 'runtime\cache\pip'),
        (Join-Path $ProjectRoot 'runtime\temp')
    )

    foreach ($ZonePath in $PythonZonePaths) {
        Test-Directory 'PYTHON ZONE' $ZonePath | Out-Null
    }

    # --------------------------------------------------------------------------
    # 06 — INVENTAIRE
    # --------------------------------------------------------------------------

    Write-Section '06 — INVENTAIRE PROJET'

    $InventoryCount = 0

    try {
        $InventoryCount = @(
            Get-ChildItem `
                -LiteralPath $ProjectRoot `
                -Recurse `
                -Force `
                -ErrorAction SilentlyContinue
        ).Count

        Add-Pass 'PROJECT INVENTORY' "$InventoryCount éléments inspectés."
    }
    catch {
        Add-Fail 'PROJECT INVENTORY' $_.Exception.Message
    }

    # --------------------------------------------------------------------------
    # 07 — JSONL / NDJSON
    # --------------------------------------------------------------------------

    Write-Section '07 — VALIDATION JSONL / NDJSON'

    $IndexJson = Join-Path $ProjectRoot 'data\index_engine_v5.json'

    if (Test-File 'JSONL FILE' $IndexJson) {

        $RecordCount = 0
        $InvalidCount = 0
        $FirstInvalidLine = $null
        $FirstInvalidMessage = $null

        try {
            $Lines = Get-Content `
                -LiteralPath $IndexJson `
                -Encoding UTF8 `
                -ErrorAction Stop

            foreach ($Line in $Lines) {

                if ([string]::IsNullOrWhiteSpace($Line)) {
                    continue
                }

                $RecordCount++

                try {
                    $null = $Line | ConvertFrom-Json -ErrorAction Stop
                }
                catch {
                    $InvalidCount++

                    if ($null -eq $FirstInvalidLine) {
                        $FirstInvalidLine = $RecordCount
                        $FirstInvalidMessage = $_.Exception.Message
                    }
                }
            }

            if ($RecordCount -gt 0 -and $InvalidCount -eq 0) {
                Add-Pass 'JSONL / NDJSON' "$IndexJson | RECORDS=$RecordCount"
            }
            else {
                $Detail = "$IndexJson | RECORDS=$RecordCount | INVALID=$InvalidCount"

                if ($null -ne $FirstInvalidLine) {
                    $Detail += " | PREMIERE_ERREUR=$FirstInvalidLine"
                    $Detail += " | $FirstInvalidMessage"
                }

                Add-Fail 'JSONL / NDJSON' $Detail
            }
        }
        catch {
            Add-Fail 'JSONL / NDJSON' "$IndexJson | $($_.Exception.Message)"
        }
    }

    # --------------------------------------------------------------------------
    # 08 — PACKAGE LOCK
    # --------------------------------------------------------------------------

    Write-Section '08 — NPM PACKAGE-LOCK'

    $PackageLock = Join-Path $ProjectRoot 'ezzio-ui\package-lock.json'

    if (Test-File 'PACKAGE-LOCK' $PackageLock) {

        try {

            $RawPackageLock = Get-Content `
                -LiteralPath $PackageLock `
                -Raw `
                -Encoding UTF8 `
                -ErrorAction Stop

            $null = $RawPackageLock |
                ConvertFrom-Json `
                    -AsHashtable `
                    -ErrorAction Stop

            Add-Pass 'PACKAGE-LOCK JSON' "$PackageLock | JSON VALIDE"
        }
        catch {
            Add-Fail 'PACKAGE-LOCK JSON' "$PackageLock | $($_.Exception.Message)"
        }
    }

    # --------------------------------------------------------------------------
    # 09 — SYNTAXE POWERSHELL
    # --------------------------------------------------------------------------

    Write-Section '09 — SYNTAXE POWERSHELL'

    $PowerShellFiles = @(
        Get-ChildItem `
            -LiteralPath $ProjectRoot `
            -Recurse `
            -File `
            -Filter '*.ps1' `
            -ErrorAction SilentlyContinue
    )

    $Ps1Checked = 0
    $Ps1Failed  = 0

    foreach ($ScriptFile in $PowerShellFiles) {

        $Tokens = $null
        $ParseErrors = $null

        try {

            [void][System.Management.Automation.Language.Parser]::ParseFile(
                $ScriptFile.FullName,
                [ref]$Tokens,
                [ref]$ParseErrors
            )

            $Ps1Checked++

            if ($ParseErrors.Count -eq 0) {
                continue
            }

            $Ps1Failed++

            $FirstError = $ParseErrors | Select-Object -First 1

            Add-Fail `
                'PS1 SYNTAX' `
                "$($ScriptFile.FullName) | ligne $($FirstError.Extent.StartLineNumber) | $($FirstError.Message)"
        }
        catch {
            $Ps1Failed++
            Add-Fail 'PS1 SYNTAX' "$($ScriptFile.FullName) | $($_.Exception.Message)"
        }
    }

    if ($Ps1Failed -eq 0) {
        Add-Pass 'PS1 SYNTAX SUMMARY' "$Ps1Checked script(s) vérifié(s), aucune erreur."
    }
    else {
        Add-Fail 'PS1 SYNTAX SUMMARY' "$Ps1Failed erreur(s) sur $Ps1Checked script(s)."
    }

    # --------------------------------------------------------------------------
    # 10 — RESIDUELS UTILISATEUR
    # --------------------------------------------------------------------------

    Write-Section '10 — RECHERCHE RESIDUELS'

    $ResidualCandidates = @(
        (Join-Path $UserRoot 'AppData\Local\Temp\EZZIO_AUDIT'),
        (Join-Path $UserRoot 'AppData\Local\Temp\EZZIO_CHIRURGICAL_VALIDATION'),
        (Join-Path $UserRoot 'AppData\Local\Temp\EZZIO_FORENSIC_CLEAN'),
        (Join-Path $UserRoot 'AppData\Local\Temp\EZZIO_GUARDIAN'),
        (Join-Path $UserRoot 'AppData\Local\Temp\EZZIO_MEMORY_FORENSIC_20260809_222237')
    )

    $ResidualCount = 0

    foreach ($ResidualPath in $ResidualCandidates) {

        if (Test-Path -LiteralPath $ResidualPath) {
            $ResidualCount++
            Add-Warn 'RESIDUAL' $ResidualPath
        }
    }

    if ($ResidualCount -eq 0) {
        Add-Pass 'RESIDUAL SCAN' 'Aucun résidu temporaire E-ZZIO connu détecté.'
    }

    # --------------------------------------------------------------------------
    # 11 — AUDIT
    # --------------------------------------------------------------------------

    Write-Section '11 — AUDIT'

    try {

        if (-not (Test-Path -LiteralPath $AuditRoot -PathType Container)) {
            Add-Warn 'AUDIT' 'Répertoire audit post-relocation absent.'
        }

        $AuditFiles = @(
            Get-ChildItem `
                -LiteralPath $AuditRoot `
                -Recurse `
                -File `
                -ErrorAction SilentlyContinue
        )

        Add-Pass 'AUDIT INVENTORY' "$($AuditFiles.Count) fichier(s) d'audit trouvé(s)."
    }
    catch {
        Add-Fail 'AUDIT INVENTORY' $_.Exception.Message
    }

    # --------------------------------------------------------------------------
    # 12 — RESULTAT
    # --------------------------------------------------------------------------

    Write-Section '12 — RESULTAT FINAL'

    Write-Host ("PASS      : {0}" -f $Passes.Count)
    Write-Host ("WARN      : {0}" -f $Warnings.Count)
    Write-Host ("FAIL      : {0}" -f $Failures.Count)

    # --------------------------------------------------------------------------
    # LOG LOCAL
    # --------------------------------------------------------------------------

    # Le validateur est READ ONLY :
    # aucun fichier de log n'est créé par cette version.
    # Les résultats sont affichés uniquement à l'écran.

    if ($Failures.Count -eq 0) {

        Write-Host ''
        Write-Host '============================================================' -ForegroundColor Green
        Write-Host ' E-ZZIO POST-RELOCATION VALIDATION : CLEAN' -ForegroundColor Green
        Write-Host '============================================================' -ForegroundColor Green

        exit 0
    }

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Red
    Write-Host ' E-ZZIO POST-RELOCATION VALIDATION : FAILURES_PRESENT' -ForegroundColor Red
    Write-Host '============================================================' -ForegroundColor Red

    exit 1
}
catch {

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Red
    Write-Host ' E-ZZIO VALIDATION ENGINE : INTERNAL ERROR' -ForegroundColor Red
    Write-Host '============================================================' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red

    exit 2
}