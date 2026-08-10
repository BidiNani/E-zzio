# ==============================================================================
# E-ZZIO CODE RELOCATION ENGINE v7.0
# ==============================================================================
#
# OBJECTIF
#   Relocaliser les artefacts E-ZZIO / Python liés à E-ZZIO depuis C:
#   vers G:\AI\E-zzio.
#
# MODES
#   DRY-RUN :
#       .\EZZIO-CodeRelocation.ps1
#
#   EXECUTION :
#       .\EZZIO-CodeRelocation.ps1 -Execute
#
#   EXECUTION + ENVIRONNEMENT :
#       .\EZZIO-CodeRelocation.ps1 -Execute -ConfigureEnvironment
#
#   ENVIRONNEMENT SEUL :
#       .\EZZIO-CodeRelocation.ps1 -ConfigureEnvironment
#
# SECURITE
#   - Aucun delete
#   - Aucun overwrite
#   - Aucun déplacement interne au projet
#   - Recent Windows exclu
#   - Startup Windows exclu
#   - Validation post-déplacement
#   - Recherche résiduelle
#   - Audit JSON + TXT + LOG
#
# COMPATIBILITE
#   PowerShell 7.x
#
# ==============================================================================

[CmdletBinding()]
param(
    [switch]$Execute,

    [switch]$ConfigureEnvironment,

    [string]$ProjectRoot = 'G:\AI\E-zzio',

    [string]$UserRoot = 'C:\Users\enrik'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ==============================================================================
# 00 — ETAT GLOBAL
# ==============================================================================

$EngineVersion = '7.0'

$StartedAt = Get-Date

# Collections volontairement simples.
# Cela évite les problèmes de typage / binding rencontrés précédemment.
$Candidates       = @()
$ValidCandidates  = @()
$ManifestEntries  = @()
$Moved            = @()
$Failed           = @()
$Skipped          = @()
$PostChecks       = @()
$Residual         = @()
$PreflightFailures = @()

$ScannedCount = 0

# ==============================================================================
# 01 — VALIDATION ROOTS
# ==============================================================================

if (-not (Test-Path -Path $ProjectRoot -PathType Container)) {
    throw "PROJECT ROOT INEXISTANT : $ProjectRoot"
}

if (-not (Test-Path -Path $UserRoot -PathType Container)) {
    throw "SEARCH ROOT INEXISTANT : $UserRoot"
}

$ProjectRoot = (Resolve-Path -Path $ProjectRoot).Path
$UserRoot    = (Resolve-Path -Path $UserRoot).Path

# ==============================================================================
# 02 — DESTINATIONS
# ==============================================================================

$DestinationMap = @{
    PYTHON   = Join-Path $ProjectRoot 'runtime\python'
    CACHE    = Join-Path $ProjectRoot 'runtime\cache'
    TEMP     = Join-Path $ProjectRoot 'runtime\temp'
    EXTERNAL = Join-Path $ProjectRoot 'runtime\external\ezzio'
    TOOLS    = Join-Path $ProjectRoot 'runtime\tools'
    DATA     = Join-Path $ProjectRoot 'runtime\data'
    AUDIT    = Join-Path $ProjectRoot 'runtime\audit\relocation'
}

# ==============================================================================
# 03 — AUDIT
# ==============================================================================

$RunStamp = Get-Date -Format 'yyyyMMdd_HHmmss'

$RunRoot = Join-Path $DestinationMap['AUDIT'] $RunStamp

New-Item `
    -Path $RunRoot `
    -ItemType Directory `
    -Force `
    -ErrorAction Stop |
    Out-Null

$LogPath      = Join-Path $RunRoot 'relocation.log'
$ManifestPath = Join-Path $RunRoot 'relocation_manifest.json'
$ResultPath   = Join-Path $RunRoot 'relocation_result.json'
$ReportPath   = Join-Path $RunRoot 'relocation_report.txt'

New-Item `
    -Path $LogPath `
    -ItemType File `
    -Force `
    -ErrorAction Stop |
    Out-Null

# ==============================================================================
# 04 — LOGGING
# ==============================================================================

function Write-Log {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    $Line = '{0} | {1}' -f `
        (Get-Date).ToString('O'),
        $Message

    Add-Content `
        -Path $LogPath `
        -Value $Line `
        -Encoding utf8
}

function Write-Section {
    param(
        [Parameter(Mandatory)]
        [string]$Title
    )

    Write-Host ''
    Write-Host '============================================================' -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host '============================================================' -ForegroundColor Cyan

    Write-Log "SECTION | $Title"
}

function Write-Info {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Host "[INFO] $Message" -ForegroundColor Gray
    Write-Log "INFO | $Message"
}

function Write-Ok {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Host "[OK]   $Message" -ForegroundColor Green
    Write-Log "OK | $Message"
}

function Write-Warn {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Host "[WARN] $Message" -ForegroundColor Yellow
    Write-Log "WARN | $Message"
}

function Write-Fail {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Host "[FAIL] $Message" -ForegroundColor Red
    Write-Log "FAIL | $Message"
}

# ==============================================================================
# 05 — NORMALISATION CHEMINS
# ==============================================================================

$ProjectRootPrefix = $ProjectRoot.TrimEnd('\') + '\'

function Test-IsInsideProject {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $Full = [string]$Path

    return $Full.StartsWith(
        $ProjectRootPrefix,
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Test-IsExcludedWindowsLocation {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $Lower = $Path.ToLowerInvariant()

    if ($Lower -match '\\appdata\\roaming\\microsoft\\windows\\recent(\\|$)') {
        return $true
    }

    if ($Lower -match '\\appdata\\roaming\\microsoft\\windows\\start menu\\programs\\startup(\\|$)') {
        return $true
    }

    return $false
}

# ==============================================================================
# 06 — MOTIFS
# ==============================================================================

$Patterns = @(
    '*EZZIO*',
    '*E-ZZIO*',
    '*E_zzio*',
    '*Ezzio*'
)

# ==============================================================================
# 07 — ENTETE
# ==============================================================================

Write-Section "E-ZZIO CODE RELOCATION ENGINE v$EngineVersion"

Write-Info "PROJECT ROOT : $ProjectRoot"
Write-Info "SEARCH ROOT  : $UserRoot"

if ($Execute) {
    Write-Info 'MODE         : EXECUTE'
}
else {
    Write-Info 'MODE         : DRY-RUN'
}

if ($ConfigureEnvironment) {
    Write-Info 'ENVIRONMENT  : CONFIGURE'
}
else {
    Write-Info 'ENVIRONMENT  : UNCHANGED'
}

Write-Info "AUDIT ROOT   : $RunRoot"

# ==============================================================================
# 08 — GARANTIES
# ==============================================================================

Write-Section '01 — GARANTIES DE SECURITE'

Write-Ok 'Projet E-ZZIO protégé contre toute relocalisation interne.'
Write-Ok 'Dry-run actif par défaut.'
Write-Info 'Aucune suppression automatique.'
Write-Info 'Aucun écrasement automatique.'
Write-Info 'Aucune modification du contenu des fichiers.'
Write-Info 'Toute destination existante sera ignorée.'
Write-Info 'Recent Windows exclu.'
Write-Info 'Startup Windows exclu.'

# ==============================================================================
# 09 — RECHERCHE
# ==============================================================================

Write-Section '02 — RECHERCHE DES ARTEFACTS'

Write-Info "SCAN ROOT : $UserRoot"

$SeenPaths = @{}

try {

    $AllItems = Get-ChildItem `
        -Path $UserRoot `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue

    foreach ($Item in $AllItems) {

        $ScannedCount++

        if ($null -eq $Item) {
            continue
        }

        $FullPath = [string]$Item.FullName

        if ([string]::IsNullOrWhiteSpace($FullPath)) {
            continue
        }

        if (Test-IsInsideProject -Path $FullPath) {
            continue
        }

        if (Test-IsExcludedWindowsLocation -Path $FullPath) {
            continue
        }

        $Matched = $false

        foreach ($Pattern in $Patterns) {

            if ($Item.Name -like $Pattern) {
                $Matched = $true
                break
            }
        }

        if (-not $Matched) {
            continue
        }

        $Key = $FullPath.ToLowerInvariant()

        if (-not $SeenPaths.ContainsKey($Key)) {
            $SeenPaths[$Key] = $true
            $Candidates += $Item
        }
    }

}
catch {
    Write-Fail "SCAN ERROR : $($_.Exception.Message)"
    throw
}

Write-Ok "ELEMENTS SCANNES : $ScannedCount"
Write-Ok "CANDIDATS BRUTS : $($Candidates.Count)"

# ==============================================================================
# 10 — NORMALISATION
# ==============================================================================

Write-Section '03 — NORMALISATION DES CANDIDATS'

$NormalizedMap = @{}

foreach ($Item in $Candidates) {

    $FullPath = [string]$Item.FullName

    if ([string]::IsNullOrWhiteSpace($FullPath)) {
        continue
    }

    $Key = $FullPath.ToLowerInvariant()

    if (-not $NormalizedMap.ContainsKey($Key)) {
        $NormalizedMap[$Key] = $Item
    }
}

$Candidates = @(
    $NormalizedMap.Values |
    Sort-Object -Property FullName
)

Write-Ok "CANDIDATS EFFECTIFS : $($Candidates.Count)"

# ==============================================================================
# 11 — CLASSIFICATION
# ==============================================================================

Write-Section '04 — CLASSIFICATION'

foreach ($Item in $Candidates) {

    $FullPath = [string]$Item.FullName

    if (Test-IsInsideProject -Path $FullPath) {
        $Skipped += [PSCustomObject]@{
            Source = $FullPath
            Reason = 'PROJECT_ROOT_PROTECTED'
        }

        continue
    }

    if (Test-IsExcludedWindowsLocation -Path $FullPath) {
        $Skipped += [PSCustomObject]@{
            Source = $FullPath
            Reason = 'WINDOWS_LOCATION_EXCLUDED'
        }

        continue
    }

    $TargetRoot = $DestinationMap['EXTERNAL']

    $LowerPath = $FullPath.ToLowerInvariant()

    if (
        ($LowerPath -match '\\\.venv(\\|$)') -or
        ($LowerPath -match '\\venv(\\|$)') -or
        ($LowerPath -match '\\site-packages(\\|$)')
    ) {
        $TargetRoot = $DestinationMap['PYTHON']
    }
    elseif (
        ($LowerPath -match '__pycache__(\\|$)') -or
        ($LowerPath -match '\\pycache(\\|$)') -or
        ($LowerPath -match '\.pyc$')
    ) {
        $TargetRoot = $DestinationMap['CACHE']
    }
    elseif (
        ($LowerPath -match '\\pip\\') -or
        ($LowerPath -match '\\pip-cache\\') -or
        ($LowerPath -match '\\cache\\')
    ) {
        $TargetRoot = $DestinationMap['CACHE']
    }
    elseif (
        ($LowerPath -match '\\temp\\') -or
        ($LowerPath -match '\\tmp\\')
    ) {
        $TargetRoot = $DestinationMap['TEMP']
    }
    elseif (
        ($LowerPath -match '\\tools\\') -or
        ($LowerPath -match '\.(py|ps1|psm1|js|ts|cmd|bat)$')
    ) {
        $TargetRoot = $DestinationMap['TOOLS']
    }

    $ValidCandidates += [PSCustomObject]@{
        Source      = $FullPath
        IsDirectory = [bool]$Item.PSIsContainer
        TargetRoot  = [string]$TargetRoot
    }
}

$ValidCandidates = @(
    $ValidCandidates |
    Sort-Object -Property Source -Unique
)

Write-Ok "CANDIDATS VALIDES : $($ValidCandidates.Count)"

# ==============================================================================
# 12 — MANIFESTE
# ==============================================================================

Write-Section '05 — CONSTRUCTION DU MANIFESTE'

foreach ($Item in $ValidCandidates) {

    $LeafName = Split-Path -Path $Item.Source -Leaf

    if ([string]::IsNullOrWhiteSpace($LeafName)) {
        $Skipped += [PSCustomObject]@{
            Source = $Item.Source
            Reason = 'EMPTY_LEAF_NAME'
        }

        continue
    }

    $Target = Join-Path `
        $Item.TargetRoot `
        $LeafName

    $ManifestEntries += [PSCustomObject]@{
        Source      = [string]$Item.Source
        Target      = [string]$Target
        IsDirectory = [bool]$Item.IsDirectory
        Status      = 'PLANNED'
    }
}

# ==============================================================================
# 13 — PREFLIGHT
# ==============================================================================

Write-Section '06 — PREFLIGHT'

foreach ($Entry in $ManifestEntries) {

    $Source = [string]$Entry.Source
    $Target = [string]$Entry.Target

    if (-not (Test-Path -Path $Source)) {

        $PreflightFailures += [PSCustomObject]@{
            Source = $Source
            Target = $Target
            Reason = 'SOURCE_NOT_FOUND'
        }

        continue
    }

    if (Test-IsInsideProject -Path $Source) {

        $PreflightFailures += [PSCustomObject]@{
            Source = $Source
            Target = $Target
            Reason = 'SOURCE_INSIDE_PROJECT'
        }

        continue
    }

    if (Test-IsExcludedWindowsLocation -Path $Source) {

        $PreflightFailures += [PSCustomObject]@{
            Source = $Source
            Target = $Target
            Reason = 'EXCLUDED_WINDOWS_LOCATION'
        }

        continue
    }

    if (Test-Path -Path $Target) {

        $Skipped += [PSCustomObject]@{
            Source = $Source
            Target = $Target
            Reason = 'TARGET_ALREADY_EXISTS'
        }
    }
}

Write-Ok "PREFLIGHT FAILURES : $($PreflightFailures.Count)"

foreach ($Failure in $PreflightFailures) {
    Write-Fail "$($Failure.Reason) | $($Failure.Source)"
}

# ==============================================================================
# 14 — PREPARATION DESTINATIONS
# ==============================================================================

Write-Section '07 — PREPARATION DES DESTINATIONS'

if ($Execute -or $ConfigureEnvironment) {

    foreach ($Destination in $DestinationMap.Values) {

        if (-not (Test-Path -Path $Destination -PathType Container)) {

            New-Item `
                -Path $Destination `
                -ItemType Directory `
                -Force `
                -ErrorAction Stop |
                Out-Null

            Write-Ok "CREATE | $Destination"
        }
    }

}
else {

    Write-Info 'DRY-RUN : création différée.'
}

# ==============================================================================
# 15 — EXECUTION
# ==============================================================================

Write-Section '08 — RELOCALISATION'

if (-not $Execute) {

    Write-Info 'DRY-RUN ACTIF : aucun déplacement effectué.'

    foreach ($Entry in $ManifestEntries) {

        Write-Host ''
        Write-Host "  SOURCE : $($Entry.Source)" -ForegroundColor DarkGray
        Write-Host "  TARGET : $($Entry.Target)" -ForegroundColor DarkCyan
    }

}
else {

    foreach ($Entry in $ManifestEntries) {

        $Source = [string]$Entry.Source
        $Target = [string]$Entry.Target

        try {

            if (-not (Test-Path -Path $Source)) {

                $Failed += [PSCustomObject]@{
                    Source = $Source
                    Target = $Target
                    Reason = 'SOURCE_NOT_FOUND'
                }

                Write-Fail "SOURCE ABSENTE | $Source"
                continue
            }

            if (Test-IsInsideProject -Path $Source) {

                $Skipped += [PSCustomObject]@{
                    Source = $Source
                    Target = $Target
                    Reason = 'PROJECT_ROOT_PROTECTED'
                }

                Write-Warn "PROJET PROTEGE | $Source"
                continue
            }

            if (Test-IsExcludedWindowsLocation -Path $Source) {

                $Skipped += [PSCustomObject]@{
                    Source = $Source
                    Target = $Target
                    Reason = 'WINDOWS_LOCATION_EXCLUDED'
                }

                Write-Warn "EXCLU WINDOWS | $Source"
                continue
            }

            if (Test-Path -Path $Target) {

                $Skipped += [PSCustomObject]@{
                    Source = $Source
                    Target = $Target
                    Reason = 'TARGET_ALREADY_EXISTS'
                }

                Write-Warn "CIBLE EXISTANTE | $Target"
                continue
            }

            $Parent = Split-Path -Path $Target -Parent

            if (-not (Test-Path -Path $Parent -PathType Container)) {

                New-Item `
                    -Path $Parent `
                    -ItemType Directory `
                    -Force `
                    -ErrorAction Stop |
                    Out-Null
            }

            Write-Info "MOVE | $Source -> $Target"

            Move-Item `
                -Path $Source `
                -Destination $Target `
                -Force:$false `
                -ErrorAction Stop

            $DestinationExists = Test-Path -Path $Target
            $SourceGone        = -not (Test-Path -Path $Source)

            if ($DestinationExists -and $SourceGone) {

                $Moved += [PSCustomObject]@{
                    Source = $Source
                    Target = $Target
                    Status = 'MOVED'
                }

                Write-Ok "MOVE VALIDATED | $Target"
            }
            else {

                $Failed += [PSCustomObject]@{
                    Source = $Source
                    Target = $Target
                    Reason = 'POST_MOVE_VALIDATION_FAILED'
                }

                Write-Fail "POST-MOVE VALIDATION FAILED | $Source"
            }

        }
        catch {

            $Message = [string]$_.Exception.Message

            $Failed += [PSCustomObject]@{
                Source = $Source
                Target = $Target
                Reason = $Message
            }

            Write-Fail "MOVE FAILED | $Source"
            Write-Log "MOVE_EXCEPTION | $Source | $Message"
        }
    }
}

# ==============================================================================
# 16 — ENVIRONNEMENT PYTHON
# ==============================================================================

Write-Section '09 — ENVIRONNEMENT PYTHON'

$EnvironmentState = @()

if ($ConfigureEnvironment) {

    $PyCache   = Join-Path $DestinationMap['CACHE'] 'pycache'
    $PipCache  = Join-Path $DestinationMap['CACHE'] 'pip'
    $EzzioTemp = $DestinationMap['TEMP']

    $EnvironmentDirectories = @(
        $PyCache,
        $PipCache,
        $EzzioTemp
    )

    foreach ($Dir in $EnvironmentDirectories) {

        if (-not (Test-Path -Path $Dir -PathType Container)) {

            New-Item `
                -Path $Dir `
                -ItemType Directory `
                -Force `
                -ErrorAction Stop |
                Out-Null
        }
    }

    $EnvAssignments = @(
        [PSCustomObject]@{
            Name  = 'EZZIO_TEMP'
            Value = [string]$EzzioTemp
        },
        [PSCustomObject]@{
            Name  = 'PYTHONPYCACHEPREFIX'
            Value = [string]$PyCache
        },
        [PSCustomObject]@{
            Name  = 'PIP_CACHE_DIR'
            Value = [string]$PipCache
        }
    )

    foreach ($Assignment in $EnvAssignments) {

        [Environment]::SetEnvironmentVariable(
            $Assignment.Name,
            $Assignment.Value,
            'User'
        )

        Set-Item `
            -Path ("Env:{0}" -f $Assignment.Name) `
            -Value $Assignment.Value `
            -ErrorAction Stop

        $EnvironmentState += [PSCustomObject]@{
            Name   = $Assignment.Name
            Value  = $Assignment.Value
            Result = 'CONFIGURED'
        }

        Write-Ok "$($Assignment.Name) = $($Assignment.Value)"
    }

    Write-Info 'TEMP/TMP Windows globaux conservés.'
    Write-Info 'E-ZZIO utilise ses zones dédiées sur G:.'

}
else {

    Write-Info 'Configuration environnement désactivée.'
}

# ==============================================================================
# 17 — VALIDATION POST-OPERATION
# ==============================================================================

Write-Section '10 — VALIDATION POST-OPERATION'

if ($Execute) {

    foreach ($Move in $Moved) {

        $DestinationExists = Test-Path -Path $Move.Target
        $SourceGone        = -not (Test-Path -Path $Move.Source)

        $Pass = (
            $DestinationExists -and
            $SourceGone
        )

        $PostChecks += [PSCustomObject]@{
            SourceGone        = [bool]$SourceGone
            DestinationExists = [bool]$DestinationExists
            Source            = [string]$Move.Source
            Target            = [string]$Move.Target
            Result             = if ($Pass) { 'PASS' } else { 'FAIL' }
        }

        if ($Pass) {
            Write-Ok "PASS | $($Move.Target)"
        }
        else {
            Write-Fail "FAIL | $($Move.Target)"
        }
    }

}
else {

    Write-Info 'DRY-RUN : validation post-déplacement différée.'
}

# ==============================================================================
# 18 — VERIFICATION ENVIRONNEMENT
# ==============================================================================

Write-Section '11 — VERIFICATION ENVIRONNEMENT'

if ($ConfigureEnvironment) {

    foreach ($Assignment in $EnvAssignments) {

        $ProcessValue = [Environment]::GetEnvironmentVariable(
            $Assignment.Name,
            'Process'
        )

        $UserValue = [Environment]::GetEnvironmentVariable(
            $Assignment.Name,
            'User'
        )

        $Pass = (
            [string]$ProcessValue -eq [string]$Assignment.Value -and
            [string]$UserValue -eq [string]$Assignment.Value
        )

        if ($Pass) {

            Write-Ok "ENV PASS | $($Assignment.Name)"

        }
        else {

            Write-Fail "ENV FAIL | $($Assignment.Name)"

            $EnvironmentState += [PSCustomObject]@{
                Name   = $Assignment.Name
                Value  = $Assignment.Value
                Result = 'VERIFICATION_FAILED'
            }
        }
    }

}
else {

    Write-Info 'ENVIRONMENT CHECK : non demandé.'
}

# ==============================================================================
# 19 — RECHERCHE RESIDUELLE
# ==============================================================================

Write-Section '12 — RECHERCHE RESIDUELLE'

$ResidualMap = @{}

try {

    $ResidualItems = Get-ChildItem `
        -Path $UserRoot `
        -Recurse `
        -Force `
        -ErrorAction SilentlyContinue

    foreach ($Item in $ResidualItems) {

        if ($null -eq $Item) {
            continue
        }

        $FullPath = [string]$Item.FullName

        if ([string]::IsNullOrWhiteSpace($FullPath)) {
            continue
        }

        if (Test-IsInsideProject -Path $FullPath) {
            continue
        }

        if (Test-IsExcludedWindowsLocation -Path $FullPath) {
            continue
        }

        $Matched = $false

        foreach ($Pattern in $Patterns) {

            if ($Item.Name -like $Pattern) {
                $Matched = $true
                break
            }
        }

        if (-not $Matched) {
            continue
        }

        $Key = $FullPath.ToLowerInvariant()

        if (-not $ResidualMap.ContainsKey($Key)) {
            $ResidualMap[$Key] = $Item
        }
    }

}
catch {

    Write-Warn "RESIDUAL SCAN ERROR | $($_.Exception.Message)"
}

$Residual = @(
    $ResidualMap.Values |
    Sort-Object -Property FullName
)

if ($Residual.Count -eq 0) {

    Write-Ok 'AUCUN ARTEFACT RESIDUEL DETECTE.'

}
else {

    Write-Warn "ARTEFACTS RESIDUELS : $($Residual.Count)"

    foreach ($Item in $Residual) {
        Write-Host "  $($Item.FullName)" -ForegroundColor Yellow
    }
}

# ==============================================================================
# 20 — STATUT GLOBAL
# ==============================================================================

$OverallStatus = 'CLEAN'

if ($Failed.Count -gt 0) {

    $OverallStatus = 'FAILURES_PRESENT'

}
elseif ($PreflightFailures.Count -gt 0) {

    $OverallStatus = 'PREFLIGHT_FAILURE'

}
elseif ($Residual.Count -gt 0) {

    $OverallStatus = 'PARTIAL_RESIDUAL'

}
elseif (-not $Execute -and $ValidCandidates.Count -gt 0) {

    $OverallStatus = 'DRY_RUN_READY'
}

# ==============================================================================
# 21 — RESULTAT
# ==============================================================================

Write-Section '13 — RESULTAT FINAL'

$DestinationReport = @{}

foreach ($Key in $DestinationMap.Keys) {
    $DestinationReport[$Key] = [string]$DestinationMap[$Key]
}

$MoveReport = @()

foreach ($Item in $Moved) {

    $MoveReport += [PSCustomObject]@{
        Source = [string]$Item.Source
        Target = [string]$Item.Target
        Status = [string]$Item.Status
    }
}

$FailureReport = @()

foreach ($Item in $Failed) {

    $FailureReport += [PSCustomObject]@{
        Source = [string]$Item.Source
        Target = [string]$Item.Target
        Reason = [string]$Item.Reason
    }
}

$SkippedReport = @()

foreach ($Item in $Skipped) {

    $SkippedReport += [PSCustomObject]@{
        Source = [string]$Item.Source
        Target = if ($Item.PSObject.Properties['Target']) {
            [string]$Item.Target
        }
        else {
            ''
        }
        Reason = [string]$Item.Reason
    }
}

$PostCheckReport = @()

foreach ($Item in $PostChecks) {

    $PostCheckReport += [PSCustomObject]@{
        SourceGone        = [bool]$Item.SourceGone
        DestinationExists = [bool]$Item.DestinationExists
        Source            = [string]$Item.Source
        Target            = [string]$Item.Target
        Result             = [string]$Item.Result
    }
}

$ResidualReport = @()

foreach ($Item in $Residual) {
    $ResidualReport += [string]$Item.FullName
}

$ManifestReport = @()

foreach ($Entry in $ManifestEntries) {

    $ManifestReport += [PSCustomObject]@{
        Source      = [string]$Entry.Source
        Target      = [string]$Entry.Target
        IsDirectory = [bool]$Entry.IsDirectory
        Status      = [string]$Entry.Status
    }
}

$PreflightReport = @()

foreach ($Item in $PreflightFailures) {

    $PreflightReport += [PSCustomObject]@{
        Source = [string]$Item.Source
        Target = [string]$Item.Target
        Reason = [string]$Item.Reason
    }
}

$Result = [PSCustomObject]@{
    EngineVersion         = $EngineVersion
    StartedAt             = $StartedAt.ToString('O')
    CompletedAt           = (Get-Date).ToString('O')

    ProjectRoot           = [string]$ProjectRoot
    SearchRoot            = [string]$UserRoot

    Execute               = [bool]$Execute
    EnvironmentConfigured = [bool]$ConfigureEnvironment

    ElementsScanned       = [int]$ScannedCount
    Candidates            = [int]$Candidates.Count
    EffectiveCandidates  = [int]$ValidCandidates.Count
    ValidCandidates       = [int]$ValidCandidates.Count

    PreflightFailures     = [int]$PreflightFailures.Count
    Moved                 = [int]$Moved.Count
    Failed                = [int]$Failed.Count
    Skipped               = [int]$Skipped.Count
    Residual              = [int]$Residual.Count

    OverallStatus         = [string]$OverallStatus

    Manifest              = [string]$ManifestPath
    Log                   = [string]$LogPath
    Report                = [string]$ReportPath

    DestinationMap        = [PSCustomObject]$DestinationReport

    ManifestEntries       = @($ManifestReport)
    Moves                 = @($MoveReport)
    Failures              = @($FailureReport)
    SkippedItems          = @($SkippedReport)
    Preflight             = @($PreflightReport)
    PostChecks            = @($PostCheckReport)
    ResidualItems         = @($ResidualReport)
    Environment           = @($EnvironmentState)
}

# ==============================================================================
# 22 — MANIFEST SERIALISATION
# ==============================================================================

try {

    $ManifestOutput = [PSCustomObject]@{
        EngineVersion       = $EngineVersion
        Timestamp           = (Get-Date).ToString('O')
        ProjectRoot         = [string]$ProjectRoot
        SearchRoot          = [string]$UserRoot
        Mode                = if ($Execute) { 'EXECUTE' } else { 'DRY-RUN' }
        Environment         = if ($ConfigureEnvironment) { 'CONFIGURE' } else { 'UNCHANGED' }
        CandidateCount      = [int]$Candidates.Count
        ValidCandidateCount = [int]$ValidCandidates.Count
        Entries             = @($ManifestReport)
    }

    $ManifestJson = $ManifestOutput |
        ConvertTo-Json -Depth 20

    Set-Content `
        -Path $ManifestPath `
        -Value $ManifestJson `
        -Encoding utf8 `
        -ErrorAction Stop

    Write-Ok "MANIFEST : $ManifestPath"

}
catch {

    Write-Fail "MANIFEST SERIALIZATION ERROR : $($_.Exception.Message)"
    $OverallStatus = 'FAILURES_PRESENT'
}

# ==============================================================================
# 23 — RESULTAT JSON
# ==============================================================================

try {

    $ResultJson = $Result |
        ConvertTo-Json -Depth 30

    Set-Content `
        -Path $ResultPath `
        -Value $ResultJson `
        -Encoding utf8 `
        -ErrorAction Stop

    Write-Ok "RESULT : $ResultPath"

}
catch {

    Write-Fail "RESULT SERIALIZATION ERROR : $($_.Exception.Message)"
    $OverallStatus = 'FAILURES_PRESENT'
}

# ==============================================================================
# 24 — RAPPORT TXT
# ==============================================================================

try {

    $ReportLines = @()

    $ReportLines += '============================================================'
    $ReportLines += " E-ZZIO CODE RELOCATION ENGINE v$EngineVersion"
    $ReportLines += '============================================================'
    $ReportLines += ''

    $ReportLines += "STATUS              : $OverallStatus"
    $ReportLines += "PROJECT ROOT        : $ProjectRoot"
    $ReportLines += "SEARCH ROOT         : $UserRoot"
    $ReportLines += "EXECUTE             : $Execute"
    $ReportLines += "ENVIRONMENT         : $ConfigureEnvironment"
    $ReportLines += "ELEMENTS SCANNED    : $ScannedCount"
    $ReportLines += "CANDIDATES          : $($Candidates.Count)"
    $ReportLines += "EFFECTIVE           : $($ValidCandidates.Count)"
    $ReportLines += "PREFLIGHT FAIL      : $($PreflightFailures.Count)"
    $ReportLines += "MOVED               : $($Moved.Count)"
    $ReportLines += "FAILED              : $($Failed.Count)"
    $ReportLines += "SKIPPED             : $($Skipped.Count)"
    $ReportLines += "RESIDUAL            : $($Residual.Count)"
    $ReportLines += ''

    $ReportLines += '-------------------- MOVES --------------------'

    foreach ($Item in $Moved) {
        $ReportLines += "MOVE | $($Item.Source) -> $($Item.Target)"
    }

    $ReportLines += ''
    $ReportLines += '-------------------- FAILURES --------------------'

    foreach ($Item in $Failed) {
        $ReportLines += "FAIL | $($Item.Source) | $($Item.Reason)"
    }

    $ReportLines += ''
    $ReportLines += '-------------------- PREFLIGHT --------------------'

    foreach ($Item in $PreflightFailures) {
        $ReportLines += "PREFLIGHT | $($Item.Source) | $($Item.Reason)"
    }

    $ReportLines += ''
    $ReportLines += '-------------------- RESIDUAL --------------------'

    foreach ($Item in $Residual) {
        $ReportLines += "RESIDUAL | $($Item.FullName)"
    }

    $ReportLines += ''
    $ReportLines += '-------------------- DESTINATIONS --------------------'

    foreach ($Key in $DestinationMap.Keys) {
        $ReportLines += "$Key = $($DestinationMap[$Key])"
    }

    Set-Content `
        -Path $ReportPath `
        -Value $ReportLines `
        -Encoding utf8 `
        -ErrorAction Stop

    Write-Ok "REPORT : $ReportPath"

}
catch {

    Write-Fail "REPORT ERROR : $($_.Exception.Message)"
    $OverallStatus = 'FAILURES_PRESENT'
}

# ==============================================================================
# 25 — AFFICHAGE FINAL
# ==============================================================================

Write-Host ''
Write-Host "ELEMENTS SCANNES   : $ScannedCount" -ForegroundColor Cyan
Write-Host "CANDIDATS          : $($Candidates.Count)" -ForegroundColor Cyan
Write-Host "EFFECTIFS          : $($ValidCandidates.Count)" -ForegroundColor Cyan
Write-Host "VALIDES            : $($ValidCandidates.Count)" -ForegroundColor Cyan
Write-Host "PREFLIGHT FAIL     : $($PreflightFailures.Count)" -ForegroundColor $(
    if ($PreflightFailures.Count -eq 0) { 'Green' } else { 'Red' }
)
Write-Host "DEPLACES           : $($Moved.Count)" -ForegroundColor $(
    if ($Moved.Count -eq 0) { 'Gray' } else { 'Green' }
)
Write-Host "ECHECS             : $($Failed.Count)" -ForegroundColor $(
    if ($Failed.Count -eq 0) { 'Green' } else { 'Red' }
)
Write-Host "IGNORES            : $($Skipped.Count)" -ForegroundColor Yellow
Write-Host "RESIDUELS          : $($Residual.Count)" -ForegroundColor $(
    if ($Residual.Count -eq 0) { 'Green' } else { 'Yellow' }
)
Write-Host ''

switch ($OverallStatus) {

    'CLEAN' {

        Write-Host '============================================================' -ForegroundColor Green
        Write-Host ' E-ZZIO RELOCATION : CLEAN' -ForegroundColor Green
        Write-Host '============================================================' -ForegroundColor Green
    }

    'DRY_RUN_READY' {

        Write-Host '============================================================' -ForegroundColor Cyan
        Write-Host ' E-ZZIO RELOCATION : DRY-RUN READY' -ForegroundColor Cyan
        Write-Host '============================================================' -ForegroundColor Cyan
    }

    'PARTIAL_RESIDUAL' {

        Write-Host '============================================================' -ForegroundColor Yellow
        Write-Host ' E-ZZIO RELOCATION : PARTIAL / RESIDUAL' -ForegroundColor Yellow
        Write-Host '============================================================' -ForegroundColor Yellow
    }

    'PREFLIGHT_FAILURE' {

        Write-Host '============================================================' -ForegroundColor Red
        Write-Host ' E-ZZIO RELOCATION : PREFLIGHT FAILURE' -ForegroundColor Red
        Write-Host '============================================================' -ForegroundColor Red
    }

    default {

        Write-Host '============================================================' -ForegroundColor Red
        Write-Host ' E-ZZIO RELOCATION : FAILURES PRESENT' -ForegroundColor Red
        Write-Host '============================================================' -ForegroundColor Red
    }
}

Write-Host ''
Write-Host "MANIFEST : $ManifestPath" -ForegroundColor Gray
Write-Host "LOG      : $LogPath" -ForegroundColor Gray
Write-Host "RESULT   : $ResultPath" -ForegroundColor Gray
Write-Host "REPORT   : $ReportPath" -ForegroundColor Gray
Write-Host ''

Write-Log "FINAL STATUS | $OverallStatus"
Write-Log (
    "SCANNED=$ScannedCount " +
    "CANDIDATES=$($Candidates.Count) " +
    "VALID=$($ValidCandidates.Count) " +
    "PREFLIGHT_FAIL=$($PreflightFailures.Count) " +
    "MOVED=$($Moved.Count) " +
    "FAILED=$($Failed.Count) " +
    "SKIPPED=$($Skipped.Count) " +
    "RESIDUAL=$($Residual.Count)"
)

Write-Host '[DONE] E-ZZIO CODE RELOCATION ENGINE TERMINE.' -ForegroundColor Green