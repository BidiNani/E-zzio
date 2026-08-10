# ==============================================================================
# E-ZZIO — FORENSIC CLEAN v2
# READ ONLY — AUCUNE MODIFICATION DU PROJET
#
# Fichier recommandé :
# G:\AI\E-zzio\EZZIO_Forensic_Clean_v2.ps1
#
# Rapports :
# %TEMP%\EZZIO_FORENSIC_CLEAN\
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ------------------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------------------

$Project = 'G:\AI\E-zzio'
$Python  = 'G:\Python312\python.exe'

$ReportDir = Join-Path $env:TEMP 'EZZIO_FORENSIC_CLEAN'
$Timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'

$ReportJson = Join-Path $ReportDir "forensic_$Timestamp.json"
$ReportTxt  = Join-Path $ReportDir "forensic_$Timestamp.txt"

$Results = [System.Collections.Generic.List[object]]::new()
$Started = Get-Date

# ------------------------------------------------------------------------------
# OUTIL RESULTAT
# ------------------------------------------------------------------------------

function Add-Result {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Id,

        [Parameter(Mandatory)]
        [ValidateSet('PASS','FAIL','WARN','INFO')]
        [string]$Status,

        [Parameter(Mandatory)]
        [string]$Message,

        $Data = $null
    )

    $Results.Add(
        [pscustomobject]@{
            Id      = $Id
            Status  = $Status
            Message = $Message
            Data    = $Data
        }
    )

    $Color = switch ($Status) {
        'PASS' { 'Green' }
        'FAIL' { 'Red' }
        'WARN' { 'Yellow' }
        'INFO' { 'Cyan' }
    }

    Write-Host "[$Status] $Id - $Message" -ForegroundColor $Color
}

# ------------------------------------------------------------------------------
# OUTIL : EXECUTION PYTHON CAPTUREE
# ------------------------------------------------------------------------------

function Invoke-PythonCapture {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments
    )

    if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
        throw "Python introuvable : $Python"
    }

    $Output = & $Python @Arguments 2>&1
    $ExitCode = $LASTEXITCODE

    [pscustomobject]@{
        ExitCode = $ExitCode
        Output   = (@($Output) -join [Environment]::NewLine)
    }
}

# ------------------------------------------------------------------------------
# OUTIL : CREATION TEMP PYTHON
# ------------------------------------------------------------------------------

function New-PythonTempFile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Prefix,

        [Parameter(Mandatory)]
        [string]$Content
    )

    $Path = Join-Path $env:TEMP (
        '{0}_{1}.py' -f
        $Prefix,
        ([guid]::NewGuid().ToString('N'))
    )

    Set-Content `
        -LiteralPath $Path `
        -Value $Content `
        -Encoding UTF8

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Impossible de créer le fichier temporaire Python : $Path"
    }

    return $Path
}

# ------------------------------------------------------------------------------
# OUTIL : TEST SYNTAXIQUE DU SCRIPT POWERSHELL LUI-MEME
# ------------------------------------------------------------------------------

function Test-PowerShellSyntax {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $Errors = $null

    [void][System.Management.Automation.Language.Parser]::ParseFile(
        $Path,
        [ref]$null,
        [ref]$Errors
    )

    if ($null -eq $Errors -or $Errors.Count -eq 0) {
        return $true
    }

    foreach ($ErrorRecord in $Errors) {
        Write-Host `
            "[SYNTAX] $($ErrorRecord.Message)" `
            -ForegroundColor Red
    }

    return $false
}

# ------------------------------------------------------------------------------
# ENTETE
# ------------------------------------------------------------------------------

Clear-Host

Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO FORENSIC CLEAN v2 — READ ONLY' -ForegroundColor Cyan
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host "Projet : $Project"
Write-Host "Python : $Python"
Write-Host ''

# ------------------------------------------------------------------------------
# 01 — ENVIRONNEMENT
# ------------------------------------------------------------------------------

Write-Host '[01/10] ENVIRONNEMENT' -ForegroundColor Cyan

if (Test-Path -LiteralPath $Project -PathType Container) {
    Add-Result `
        -Id 'ENV-001' `
        -Status 'PASS' `
        -Message "Projet accessible : $Project"
}
else {
    Add-Result `
        -Id 'ENV-001' `
        -Status 'FAIL' `
        -Message "Projet introuvable : $Project"
}

if (Test-Path -LiteralPath $Python -PathType Leaf) {
    try {
        $PythonVersion = Invoke-PythonCapture -Arguments @('--version')

        if ($PythonVersion.ExitCode -eq 0) {
            Add-Result `
                -Id 'ENV-002' `
                -Status 'PASS' `
                -Message $PythonVersion.Output.Trim()
        }
        else {
            Add-Result `
                -Id 'ENV-002' `
                -Status 'FAIL' `
                -Message 'Python répond avec un code erreur.' `
                -Data $PythonVersion.Output
        }
    }
    catch {
        Add-Result `
            -Id 'ENV-002' `
            -Status 'FAIL' `
            -Message 'Impossible d''exécuter Python.' `
            -Data $_.Exception.Message
    }
}
else {
    Add-Result `
        -Id 'ENV-002' `
        -Status 'FAIL' `
        -Message "Python introuvable : $Python"
}

# ------------------------------------------------------------------------------
# 02 — MEMORY CORE
# ------------------------------------------------------------------------------

Write-Host '[02/10] MEMORY CORE' -ForegroundColor Cyan

$MemoryCore = Join-Path $Project 'core\memory_core.py'

if (Test-Path -LiteralPath $MemoryCore -PathType Leaf) {
    $Item = Get-Item -LiteralPath $MemoryCore

    Add-Result `
        -Id 'FILE-MEM' `
        -Status 'PASS' `
        -Message "memory_core.py présent ($($Item.Length) octets)"
}
else {
    Add-Result `
        -Id 'FILE-MEM' `
        -Status 'FAIL' `
        -Message "memory_core.py absent : $MemoryCore"
}

# ------------------------------------------------------------------------------
# 03 — DECOUVERTE WEB SERVER
# ------------------------------------------------------------------------------

Write-Host '[03/10] WEB SERVER — DECOUVERTE REELLE' -ForegroundColor Cyan

$WebCandidates = @()

if (Test-Path -LiteralPath $Project -PathType Container) {
    $WebCandidates = @(
        Get-ChildItem `
            -LiteralPath $Project `
            -File `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq 'web_server.py'
        }
    )
}

$WebServer = $null

if ($WebCandidates.Count -eq 0) {
    Add-Result `
        -Id 'FILE-WEB' `
        -Status 'FAIL' `
        -Message 'Aucun fichier web_server.py trouvé dans le projet.'
}
else {
    foreach ($File in $WebCandidates) {
        Add-Result `
            -Id 'FILE-WEB' `
            -Status 'PASS' `
            -Message "Trouvé : $($File.FullName) ($($File.Length) octets)"
    }

    $PreferredPaths = @(
        (Join-Path $Project 'web\web_server.py'),
        (Join-Path $Project 'web_server.py'),
        (Join-Path $Project 'web_server.py')
    )

    foreach ($PreferredPath in $PreferredPaths) {
        $Candidate = $WebCandidates |
            Where-Object {
                $_.FullName -eq $PreferredPath
            } |
            Select-Object -First 1

        if ($null -ne $Candidate) {
            $WebServer = $Candidate.FullName
            break
        }
    }

    if ($null -eq $WebServer) {
        $WebServer = (
            $WebCandidates |
            Sort-Object FullName |
            Select-Object -First 1
        ).FullName
    }

    Add-Result `
        -Id 'FILE-WEB-ACTIVE' `
        -Status 'INFO' `
        -Message "Fichier retenu : $WebServer"
}

# ------------------------------------------------------------------------------
# 04 — SQLITE
# ------------------------------------------------------------------------------

Write-Host '[04/10] SQLITE' -ForegroundColor Cyan

$DbCandidates = @(
    (Join-Path $Project 'runtime\memory\database\memory.sqlite3')
    (Join-Path $Project 'runtime\memory\sqlite\cognitive_store.db')
    (Join-Path $Project 'data\action_registry.db')
)

$MemoryDb = $null

foreach ($CandidatePath in $DbCandidates) {
    if (Test-Path -LiteralPath $CandidatePath -PathType Leaf) {
        $MemoryDb = $CandidatePath
        break
    }
}

if ($null -eq $MemoryDb -and
    (Test-Path -LiteralPath $Project -PathType Container)) {

    $FoundDatabases = @(
        Get-ChildItem `
            -LiteralPath $Project `
            -File `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Extension -in @('.db','.sqlite','.sqlite3')
        }
    )

    if ($FoundDatabases.Count -gt 0) {
        $MemoryDb = (
            $FoundDatabases |
            Sort-Object Length -Descending |
            Select-Object -First 1
        ).FullName
    }
}

if ($null -ne $MemoryDb) {
    $DbItem = Get-Item -LiteralPath $MemoryDb

    Add-Result `
        -Id 'SQLITE-001' `
        -Status 'PASS' `
        -Message "Base trouvée : $MemoryDb ($($DbItem.Length) octets)"
}
else {
    Add-Result `
        -Id 'SQLITE-001' `
        -Status 'FAIL' `
        -Message 'Aucune base SQLite trouvée.'
}

# ------------------------------------------------------------------------------
# 05 — SYNTAXE PYTHON
# ------------------------------------------------------------------------------

Write-Host '[05/10] SYNTAXE PYTHON' -ForegroundColor Cyan

$PythonTargets = @()

if (Test-Path -LiteralPath $MemoryCore -PathType Leaf) {
    $PythonTargets += $MemoryCore
}

if ($null -ne $WebServer -and
    (Test-Path -LiteralPath $WebServer -PathType Leaf)) {
    $PythonTargets += $WebServer
}

foreach ($PythonFile in $PythonTargets) {

    try {
        $CompileResult = Invoke-PythonCapture `
            -Arguments @(
                '-m',
                'py_compile',
                $PythonFile
            )

        if ($CompileResult.ExitCode -eq 0) {
            Add-Result `
                -Id 'PY-COMPILE' `
                -Status 'PASS' `
                -Message "Syntaxe Python valide : $PythonFile"
        }
        else {
            Add-Result `
                -Id 'PY-COMPILE' `
                -Status 'FAIL' `
                -Message "Erreur de syntaxe Python : $PythonFile" `
                -Data $CompileResult.Output
        }
    }
    catch {
        Add-Result `
            -Id 'PY-COMPILE' `
            -Status 'FAIL' `
            -Message "Échec du contrôle Python : $PythonFile" `
            -Data $_.Exception.Message
    }
}

# ------------------------------------------------------------------------------
# 06 — IMPORTS PYTHON
# ------------------------------------------------------------------------------

Write-Host '[06/10] DEPENDANCES PYTHON' -ForegroundColor Cyan

$ImportScript = @'
import importlib
import sys

modules = [
    "sqlite3",
    "pathlib",
    "datetime",
    "fastapi",
    "pydantic",
    "google.genai",
    "dotenv",
    "aiohttp",
]

failed = []

for name in modules:
    try:
        importlib.import_module(name)
        print("OK=" + name)
    except Exception as exc:
        failed.append(name)
        print(
            "FAIL=" +
            name +
            " :: " +
            type(exc).__name__ +
            " :: " +
            str(exc)
        )

if failed:
    sys.exit(1)

sys.exit(0)
'@

$ImportTemp = $null

try {
    $ImportTemp = New-PythonTempFile `
        -Prefix 'ezzio_import' `
        -Content $ImportScript

    $ImportResult = Invoke-PythonCapture `
        -Arguments @($ImportTemp)

    if ($ImportResult.ExitCode -eq 0) {
        Add-Result `
            -Id 'IMPORTS' `
            -Status 'PASS' `
            -Message 'Dépendances Python disponibles.' `
            -Data $ImportResult.Output
    }
    else {
        Add-Result `
            -Id 'IMPORTS' `
            -Status 'FAIL' `
            -Message 'Une ou plusieurs dépendances Python sont absentes/inutilisables.' `
            -Data $ImportResult.Output
    }
}
catch {
    Add-Result `
        -Id 'IMPORTS' `
        -Status 'FAIL' `
        -Message 'Échec du test des dépendances Python.' `
        -Data $_.Exception.Message
}
finally {
    if ($null -ne $ImportTemp -and
        (Test-Path -LiteralPath $ImportTemp -PathType Leaf)) {

        Remove-Item `
            -LiteralPath $ImportTemp `
            -Force `
            -ErrorAction SilentlyContinue
    }
}

# ------------------------------------------------------------------------------
# 07 — SQLITE READ ONLY
# ------------------------------------------------------------------------------

Write-Host '[07/10] SQLITE — READ ONLY' -ForegroundColor Cyan

if ($null -ne $MemoryDb) {

    $SqliteScript = @'
import sqlite3
import sys
import json

path = sys.argv[1]

try:
    uri = "file:" + path.replace("\\", "/") + "?mode=ro"

    conn = sqlite3.connect(uri, uri=True)

    tables = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """).fetchall()

    table_names = [row[0] for row in tables]

    print(
        "TABLES=" +
        json.dumps(table_names, ensure_ascii=False)
    )

    if "interactions" not in table_names:
        print("INTERACTIONS_MISSING")
        conn.close()
        sys.exit(10)

    columns = conn.execute(
        "PRAGMA table_info(interactions)"
    ).fetchall()

    print(
        "INTERACTIONS_COLUMNS=" +
        json.dumps(
            [
                {
                    "cid": row[0],
                    "name": row[1],
                    "type": row[2],
                    "notnull": row[3],
                    "default": row[4],
                    "pk": row[5]
                }
                for row in columns
            ],
            ensure_ascii=False
        )
    )

    conn.close()

    print("SQLITE_READONLY_OK")
    sys.exit(0)

except Exception as exc:
    print(type(exc).__name__ + ": " + str(exc))
    sys.exit(1)
'@

    $SqliteTemp = $null

    try {
        $SqliteTemp = New-PythonTempFile `
            -Prefix 'ezzio_sqlite' `
            -Content $SqliteScript

        $SqliteResult = Invoke-PythonCapture `
            -Arguments @(
                $SqliteTemp,
                $MemoryDb
            )

        if ($SqliteResult.ExitCode -eq 0) {
            Add-Result `
                -Id 'SQLITE-002' `
                -Status 'PASS' `
                -Message 'SQLite accessible en mode READ ONLY.' `
                -Data $SqliteResult.Output
        }
        elseif ($SqliteResult.ExitCode -eq 10) {
            Add-Result `
                -Id 'SQLITE-002' `
                -Status 'FAIL' `
                -Message 'Table interactions absente.' `
                -Data $SqliteResult.Output
        }
        else {
            Add-Result `
                -Id 'SQLITE-002' `
                -Status 'FAIL' `
                -Message 'Lecture SQLite impossible.' `
                -Data $SqliteResult.Output
        }
    }
    catch {
        Add-Result `
            -Id 'SQLITE-002' `
            -Status 'FAIL' `
            -Message 'Exception pendant le contrôle SQLite.' `
            -Data $_.Exception.Message
    }
    finally {
        if ($null -ne $SqliteTemp -and
            (Test-Path -LiteralPath $SqliteTemp -PathType Leaf)) {

            Remove-Item `
                -LiteralPath $SqliteTemp `
                -Force `
                -ErrorAction SilentlyContinue
        }
    }
}
else {
    Add-Result `
        -Id 'SQLITE-002' `
        -Status 'WARN' `
        -Message 'Contrôle SQLite ignoré : aucune base identifiée.'
}

# ------------------------------------------------------------------------------
# 08 — HEALTH
# ------------------------------------------------------------------------------

Write-Host '[08/10] HEALTH ENDPOINT' -ForegroundColor Cyan

$HealthUrl = 'http://127.0.0.1:8001/health'

try {
    $Health = Invoke-WebRequest `
        -Uri $HealthUrl `
        -Method GET `
        -TimeoutSec 3 `
        -ErrorAction Stop

    if ($Health.StatusCode -eq 200) {
        Add-Result `
            -Id 'HEALTH-001' `
            -Status 'PASS' `
            -Message '/health répond HTTP 200.' `
            -Data $Health.Content
    }
    else {
        Add-Result `
            -Id 'HEALTH-001' `
            -Status 'WARN' `
            -Message "/health répond HTTP $($Health.StatusCode)." `
            -Data $Health.Content
    }
}
catch {
    Add-Result `
        -Id 'HEALTH-001' `
        -Status 'WARN' `
        -Message 'Démon non joignable sur 127.0.0.1:8001.' `
        -Data $_.Exception.Message
}

# ------------------------------------------------------------------------------
# 09 — GUARDIAN
# ------------------------------------------------------------------------------

Write-Host '[09/10] GUARDIAN BACKUPS' -ForegroundColor Cyan

$RuntimeRoot = Join-Path $Project 'runtime'
$RuntimeBackups = @()

if (Test-Path -LiteralPath $RuntimeRoot -PathType Container) {

    $RuntimeBackups = @(
        Get-ChildItem `
            -LiteralPath $RuntimeRoot `
            -Directory `
            -Filter 'guardian.backup-*' `
            -Force `
            -ErrorAction SilentlyContinue
    )
}

if ($RuntimeBackups.Count -eq 0) {
    Add-Result `
        -Id 'GUARDIAN-001' `
        -Status 'PASS' `
        -Message 'Aucun guardian.backup-* dans runtime.'
}
else {
    Add-Result `
        -Id 'GUARDIAN-001' `
        -Status 'WARN' `
        -Message "$($RuntimeBackups.Count) backup(s) Guardian présents dans runtime." `
        -Data @($RuntimeBackups.FullName)
}

# ------------------------------------------------------------------------------
# 10 — INTEGRITE / HASH
# ------------------------------------------------------------------------------

Write-Host '[10/10] INTEGRITE SHA256' -ForegroundColor Cyan

$HashTargets = @()

foreach ($Path in @($MemoryCore, $WebServer, $MemoryDb)) {

    if ($null -ne $Path -and
        (Test-Path -LiteralPath $Path -PathType Leaf)) {

        $HashTargets += $Path
    }
}

$Hashes = [ordered]@{}

foreach ($Path in $HashTargets) {

    try {
        $Hash = Get-FileHash `
            -LiteralPath $Path `
            -Algorithm SHA256 `
            -ErrorAction Stop

        $Hashes[$Path] = $Hash.Hash

        Add-Result `
            -Id 'HASH' `
            -Status 'PASS' `
            -Message "SHA256 $Path = $($Hash.Hash)" `
            -Data $Hash.Hash
    }
    catch {
        Add-Result `
            -Id 'HASH' `
            -Status 'FAIL' `
            -Message "Impossible de calculer SHA256 : $Path" `
            -Data $_.Exception.Message
    }
}

# ------------------------------------------------------------------------------
# SYNTHESE
# ------------------------------------------------------------------------------

$Finished = Get-Date
$Duration = $Finished - $Started

$Pass = @(
    $Results | Where-Object { $_.Status -eq 'PASS' }
).Count

$Fail = @(
    $Results | Where-Object { $_.Status -eq 'FAIL' }
).Count

$Warn = @(
    $Results | Where-Object { $_.Status -eq 'WARN' }
).Count

$Info = @(
    $Results | Where-Object { $_.Status -eq 'INFO' }
).Count

$Overall = if ($Fail -gt 0) {
    'FAIL'
}
elseif ($Warn -gt 0) {
    'PASS_WITH_WARNINGS'
}
else {
    'PASS'
}

# ------------------------------------------------------------------------------
# RAPPORT TEMP
# ------------------------------------------------------------------------------

if (-not (Test-Path -LiteralPath $ReportDir -PathType Container)) {
    New-Item `
        -ItemType Directory `
        -LiteralPath $ReportDir `
        -Force |
        Out-Null
}

$Report = [ordered]@{
    Validation            = 'E-ZZIO FORENSIC CLEAN v2'
    Mode                  = 'READ_ONLY'
    ModificationPerformed = $false
    Project               = $Project
    Python                = $Python
    MemoryCore            = $MemoryCore
    WebServer             = $WebServer
    MemoryDb              = $MemoryDb
    Started               = $Started.ToString('o')
    Finished              = $Finished.ToString('o')
    DurationMs            = [math]::Round(
        $Duration.TotalMilliseconds,
        2
    )
    Summary               = [ordered]@{
        Overall = $Overall
        PASS    = $Pass
        FAIL    = $Fail
        WARN    = $Warn
        INFO    = $Info
        Total   = $Results.Count
    }
    Hashes                = $Hashes
    Results               = $Results
}

$Report |
    ConvertTo-Json -Depth 12 |
    Set-Content `
        -LiteralPath $ReportJson `
        -Encoding UTF8

$Lines = @(
    'E-ZZIO FORENSIC CLEAN v2'
    'MODE : READ_ONLY'
    "Overall : $Overall"
    "PASS=$Pass FAIL=$Fail WARN=$Warn INFO=$Info"
    "Total=$($Results.Count)"
    "Project : $Project"
    "MemoryCore : $MemoryCore"
    "WebServer : $WebServer"
    "MemoryDb : $MemoryDb"
    ''
)

foreach ($Result in $Results) {
    $Lines += (
        '[{0}] {1} - {2}' -f
        $Result.Status,
        $Result.Id,
        $Result.Message
    )
}

$Lines |
    Set-Content `
        -LiteralPath $ReportTxt `
        -Encoding UTF8

# ------------------------------------------------------------------------------
# SORTIE
# ------------------------------------------------------------------------------

$OverallColor = switch ($Overall) {
    'PASS'               { 'Green' }
    'PASS_WITH_WARNINGS' { 'Yellow' }
    'FAIL'               { 'Red' }
}

Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host " PASS : $Pass" -ForegroundColor Green
Write-Host " FAIL : $Fail" -ForegroundColor $(if ($Fail -gt 0) { 'Red' } else { 'Green' })
Write-Host " WARN : $Warn" -ForegroundColor $(if ($Warn -gt 0) { 'Yellow' } else { 'Green' })
Write-Host " INFO : $Info" -ForegroundColor Cyan
Write-Host " TOTAL: $($Results.Count)" -ForegroundColor White
Write-Host ''
Write-Host " RÉSULTAT GLOBAL : $Overall" -ForegroundColor $OverallColor
Write-Host ''
Write-Host " Rapport JSON : $ReportJson" -ForegroundColor DarkGray
Write-Host " Rapport TXT  : $ReportTxt" -ForegroundColor DarkGray
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host ''