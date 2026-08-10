# ==============================================================================
# E-ZZIO — FORENSIC CLEAN v1
# READ ONLY — rapport uniquement dans TEMP
# À EXÉCUTER EN FICHIER : .\EZZIO_Forensic_Clean_v1.ps1
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Project = 'G:\AI\E-zzio'
$Python  = 'G:\Python312\python.exe'

$ReportDir  = Join-Path $env:TEMP 'EZZIO_FORENSIC_CLEAN'
$Timestamp  = Get-Date -Format 'yyyyMMdd_HHmmss'
$ReportJson = Join-Path $ReportDir "forensic_$Timestamp.json"
$ReportTxt  = Join-Path $ReportDir "forensic_$Timestamp.txt"

$Results = [System.Collections.Generic.List[object]]::new()
$Started = Get-Date

function Add-Result {
    param(
        [string]$Id,
        [string]$Status,   # PASS | FAIL | WARN | INFO
        [string]$Message,
        $Data = $null
    )
    $Results.Add([pscustomobject]@{
        Id      = $Id
        Status  = $Status
        Message = $Message
        Data    = $Data
    })
    $color = switch ($Status) {
        'PASS' { 'Green' }
        'FAIL' { 'Red' }
        'WARN' { 'Yellow' }
        default { 'Cyan' }
    }
    Write-Host "[$Status] $Id - $Message" -ForegroundColor $color
}

# ------------------------------------------------------------------------------
Clear-Host
Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO FORENSIC CLEAN v1 — READ ONLY' -ForegroundColor Cyan
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host ''

# 01 Projet / Python
if (-not (Test-Path -LiteralPath $Project -PathType Container)) {
    throw "Projet introuvable : $Project"
}
Add-Result 'ENV-001' 'PASS' "Projet OK : $Project"

if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Python introuvable : $Python"
}
$ver = & $Python --version 2>&1
Add-Result 'ENV-002' 'PASS' "$ver"

# 02 MemoryCore (chemin confirmé)
$MemoryCore = Join-Path $Project 'core\memory_core.py'
if (Test-Path -LiteralPath $MemoryCore -PathType Leaf) {
    $item = Get-Item -LiteralPath $MemoryCore
    Add-Result 'FILE-MEM' 'PASS' "memory_core.py présent ($($item.Length) octets)"
} else {
    Add-Result 'FILE-MEM' 'FAIL' "memory_core.py absent : $MemoryCore"
}

# 03 web_server — découverte réelle
$WebCandidates = @(
    Get-ChildItem -LiteralPath $Project -File -Recurse -Force -ErrorAction SilentlyContinue |
    Where-Object {
        $_.Name -eq 'web_server.py' -or
        $_.Name -eq '_server.py' -or
        ($_.Name -like '*web*server*.py')
    }
)

if ($WebCandidates.Count -eq 0) {
    Add-Result 'FILE-WEB' 'FAIL' 'Aucun web_server.py trouvé dans le projet'
    $WebServer = $null
} else {
    foreach ($f in $WebCandidates) {
        Add-Result 'FILE-WEB' 'PASS' "Trouvé : $($f.FullName) ($($f.Length) octets)"
    }
    # Priorité : web\web_server.py > racine > premier trouvé
    $preferred = $WebCandidates | Where-Object { $_.FullName -eq (Join-Path $Project 'web\web_server.py') } | Select-Object -First 1
    if (-not $preferred) {
        $preferred = $WebCandidates | Where-Object { $_.FullName -eq (Join-Path $Project 'web_server.py') } | Select-Object -First 1
    }
    if (-not $preferred) {
        $preferred = $WebCandidates | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    }
    $WebServer = $preferred.FullName
    Add-Result 'FILE-WEB-ACTIVE' 'INFO' "Fichier retenu : $WebServer"
}

# 04 SQLite (chemin confirmé + fallback)
$DbCandidates = @(
    (Join-Path $Project 'runtime\memory\database\memory.sqlite3')
    (Join-Path $Project 'runtime\memory\sqlite\cognitive_store.db')
    (Join-Path $Project 'data\action_registry.db')
)

$MemoryDb = $null
foreach ($c in $DbCandidates) {
    if (Test-Path -LiteralPath $c -PathType Leaf) {
        $MemoryDb = $c
        break
    }
}
if ($null -eq $MemoryDb) {
    $found = @(
        Get-ChildItem -LiteralPath $Project -File -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in '.db','.sqlite','.sqlite3' }
    )
    if ($found.Count -ge 1) {
        $MemoryDb = ($found | Sort-Object Length -Descending | Select-Object -First 1).FullName
    }
}

if ($null -ne $MemoryDb) {
    $dbItem = Get-Item -LiteralPath $MemoryDb
    Add-Result 'SQLITE' 'PASS' "Base : $MemoryDb ($($dbItem.Length) octets)"
} else {
    Add-Result 'SQLITE' 'FAIL' 'Aucune base SQLite trouvée'
}

# 05 Syntaxe memory_core
if (Test-Path -LiteralPath $MemoryCore -PathType Leaf) {
    & $Python -m py_compile $MemoryCore 2>$null
    if ($LASTEXITCODE -eq 0) {
        Add-Result 'PY-MEM' 'PASS' 'memory_core.py : syntaxe OK'
    } else {
        Add-Result 'PY-MEM' 'FAIL' 'memory_core.py : erreur de syntaxe'
    }
}

# 06 Syntaxe web_server (si trouvé)
if ($null -ne $WebServer) {
    & $Python -m py_compile $WebServer 2>$null
    if ($LASTEXITCODE -eq 0) {
        Add-Result 'PY-WEB' 'PASS' 'web_server : syntaxe OK'
    } else {
        Add-Result 'PY-WEB' 'FAIL' 'web_server : erreur de syntaxe'
    }
}

# 07 Health
try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8001/health' -TimeoutSec 3 -ErrorAction Stop
    if ($r.StatusCode -eq 200) {
        Add-Result 'HEALTH' 'PASS' '/health HTTP 200'
    } else {
        Add-Result 'HEALTH' 'WARN' "/health HTTP $($r.StatusCode)"
    }
} catch {
    Add-Result 'HEALTH' 'WARN' 'Démon non joignable sur :8001'
}

# 08 Guardian runtime
$runtimeBackups = @(
    Get-ChildItem -LiteralPath (Join-Path $Project 'runtime') -Directory -Filter 'guardian.backup-*' -Force -ErrorAction SilentlyContinue
)
if ($runtimeBackups.Count -eq 0) {
    Add-Result 'GUARDIAN' 'PASS' 'Aucun guardian.backup-* dans runtime'
} else {
    Add-Result 'GUARDIAN' 'WARN' "$($runtimeBackups.Count) backup(s) encore dans runtime"
}

# ------------------------------------------------------------------------------
# Synthèse + rapport TEMP
# ------------------------------------------------------------------------------
$Pass = @($Results | Where-Object Status -eq 'PASS').Count
$Fail = @($Results | Where-Object Status -eq 'FAIL').Count
$Warn = @($Results | Where-Object Status -eq 'WARN').Count
$Info = @($Results | Where-Object Status -eq 'INFO').Count

$Overall = if ($Fail -gt 0) { 'FAIL' } elseif ($Warn -gt 0) { 'PASS_WITH_WARNINGS' } else { 'PASS' }

if (-not (Test-Path -LiteralPath $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
}

$Report = [ordered]@{
    Validation = 'E-ZZIO FORENSIC CLEAN v1'
    Project    = $Project
    MemoryCore = $MemoryCore
    WebServer  = $WebServer
    MemoryDb   = $MemoryDb
    Overall    = $Overall
    PASS       = $Pass
    FAIL       = $Fail
    WARN       = $Warn
    INFO       = $Info
    Results    = $Results
    Finished   = (Get-Date).ToString('o')
}

$Report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $ReportJson -Encoding UTF8

$lines = @(
    'E-ZZIO FORENSIC CLEAN v1'
    "Overall : $Overall"
    "PASS=$Pass FAIL=$Fail WARN=$Warn INFO=$Info"
    "MemoryCore : $MemoryCore"
    "WebServer  : $WebServer"
    "MemoryDb   : $MemoryDb"
    ''
)
foreach ($r in $Results) {
    $lines += "[$($r.Status)] $($r.Id) - $($r.Message)"
}
$lines | Set-Content -LiteralPath $ReportTxt -Encoding UTF8

Write-Host ''
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host " RÉSULTAT GLOBAL : $Overall" -ForegroundColor $(if ($Fail -gt 0) { 'Red' } elseif ($Warn -gt 0) { 'Yellow' } else { 'Green' })
Write-Host " PASS=$Pass  FAIL=$Fail  WARN=$Warn  INFO=$Info"
Write-Host " Rapport : $ReportTxt" -ForegroundColor DarkGray
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host ''