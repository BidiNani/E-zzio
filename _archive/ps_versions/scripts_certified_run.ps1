# ==============================================================================
# E-ZZIO — 100% QUALITY FORENSIC CERTIFIER (OFFICIEL V6.2)
# ==============================================================================

$ErrorActionPreference = "Continue"
$ProjectRoot = "G:\AI\E-zzio"
$PythonExe   = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location -LiteralPath $ProjectRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$Start = Get-Date
$RunId = Get-Date -Format "yyyyMMdd_HHmmss"

$AuditRoot = Join-Path $ProjectRoot "runtime\audit\certification"
$ReportDir = Join-Path $AuditRoot $RunId
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

$Results = [System.Collections.Generic.List[object]]::new()

function Add-Gate {
    param([string]$Name, [string]$Status, [string]$Message, [string]$Evidence = "")
    $obj = [PSCustomObject]@{ Gate = $Name; Status = $Status; Message = $Message; Evidence = $Evidence }
    $Results.Add($obj)

    switch ($Status) {
        "PASS" { Write-Host "[PASS] $Name :: $Message" -ForegroundColor Green }
        "FAIL" { Write-Host "[FAIL] $Name :: $Message" -ForegroundColor Red }
        "WARN" { Write-Host "[WARN] $Name :: $Message" -ForegroundColor Yellow }
    }
}

function Get-RelativePath {
    param([string]$Path)
    return $Path.Substring($ProjectRoot.Length).TrimStart('\')
}

Write-Host "`n==============================================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — 100% QUALITY FORENSIC CERTIFIER" -ForegroundColor Cyan
Write-Host " MODE : FAST + FORENSIC | READ-ONLY | FAIL-CLOSED" -ForegroundColor Cyan
Write-Host " RUN  : $RunId" -ForegroundColor DarkCyan
Write-Host "==============================================================================`n" -ForegroundColor Cyan

# ------------------------------------------------------------------------------
# GATES FONDAMENTAUX
# ------------------------------------------------------------------------------
if (Test-Path -LiteralPath $ProjectRoot -PathType Container) {
    Add-Gate "PROJECT" "PASS" "Project root accessible"
} else {
    Add-Gate "PROJECT" "FAIL" "Project root inaccessible"
}

if (Test-Path -LiteralPath $PythonExe -PathType Leaf) {
    $pyVer = & $PythonExe --version 2>&1
    Add-Gate "PYTHON" "PASS" "$($pyVer.ToString().Trim())"
} else {
    Add-Gate "PYTHON" "FAIL" "Environnement virtuel Python absent"
}

# ------------------------------------------------------------------------------
# INVENTAIRE FORENSIC (FILTRAGE DES DOSSIERS SYSTÈMES / TIERS)
# ------------------------------------------------------------------------------
$ExcludedRegex = '\\(\.venv|\.git|node_modules|__pycache__|reports)(\\|$)'
$AllFiles = @(Get-ChildItem -LiteralPath $ProjectRoot -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch $ExcludedRegex })

$PythonFiles = @($AllFiles | Where-Object Extension -ieq ".py")
$JsonFiles   = @($AllFiles | Where-Object Extension -ieq ".json")
$JsonlFiles  = @($AllFiles | Where-Object Extension -ieq ".jsonl")
$SqliteFiles = @($AllFiles | Where-Object { $_.Extension.ToLowerInvariant() -in @(".db",".sqlite",".sqlite3") })

Add-Gate "INVENTORY" "PASS" "$($AllFiles.Count) fichiers dans le périmètre source"

# ------------------------------------------------------------------------------
# CONTRÔLE STATIQUE RUFF
# ------------------------------------------------------------------------------
$RuffOutput = @(& $PythonExe -m ruff check . --exclude ".venv" --exclude "tools/voice_converter/.venv" --output-format concise 2>&1)
if ($LASTEXITCODE -eq 0) {
    Add-Gate "RUFF" "PASS" "0 anomalie détectée"
} else {
    $RuffOutput | Set-Content -LiteralPath (Join-Path $ReportDir "ruff.txt") -Encoding UTF8
    Add-Gate "RUFF" "FAIL" "Erreurs de conformité détectées"
}

# ------------------------------------------------------------------------------
# COMPILATION BYTECODE (ISOLÉE)
# ------------------------------------------------------------------------------
$CompileOutput = @(& $PythonExe -m compileall -q -x "[\\/](\.venv|node_modules|\.git)" . 2>&1)
if ($LASTEXITCODE -eq 0) {
    Add-Gate "BYTECODE" "PASS" "Compilation bytecode complète réussie"
} else {
    Add-Gate "BYTECODE" "FAIL" "Erreur lors de la compilation bytecode"
}

# ------------------------------------------------------------------------------
# SYNTAXE AST PYTHON
# ------------------------------------------------------------------------------
$AstFailures = [System.Collections.Generic.List[string]]::new()
foreach ($file in $PythonFiles) {
    $cmd = "import ast; p=r'''$($file.FullName)'''; ast.parse(open(p, encoding='utf-8').read(), filename=p)"
    & $PythonExe -c $cmd 2>$null
    if ($LASTEXITCODE -ne 0) { $AstFailures.Add((Get-RelativePath $file.FullName)) }
}

if ($AstFailures.Count -eq 0) {
    Add-Gate "PYTHON_AST" "PASS" "$($PythonFiles.Count) modules Python syntaxiquement valides"
} else {
    Add-Gate "PYTHON_AST" "FAIL" "$($AstFailures.Count) erreurs de syntaxe AST"
}

# ------------------------------------------------------------------------------
# BASES DE DONNÉES SQLITE
# ------------------------------------------------------------------------------
$SqliteFailures = [System.Collections.Generic.List[string]]::new()
foreach ($db in $SqliteFiles) {
    $cmd = "import sqlite3, sys; c=sqlite3.connect(r'''$($db.FullName)'''); res=c.execute('PRAGMA integrity_check;').fetchone()[0]; c.close(); sys.exit(0 if str(res).lower() == 'ok' else 1)"
    & $PythonExe -c $cmd 2>$null
    if ($LASTEXITCODE -ne 0) { $SqliteFailures.Add((Get-RelativePath $db.FullName)) }
}

if ($SqliteFailures.Count -eq 0) {
    Add-Gate "SQLITE" "PASS" "$($SqliteFiles.Count) bases SQLite intègres"
} else {
    Add-Gate "SQLITE" "FAIL" "$($SqliteFailures.Count) bases SQLite corrompues"
}

# ------------------------------------------------------------------------------
# SUITE DE TESTS PYTEST
# ------------------------------------------------------------------------------
# Chargement du .env pour les clés d'API nécessaires aux tests
if (Test-Path ".env") {
    Get-Content ".env" | Where-Object { $_ -notmatch "^#" -and $_ -match "=" } | ForEach-Object {
        $k, $v = $_.Split("=", 2)
        [System.Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim(), "Process")
    }
}

$PytestOutput = @(& $PythonExe -m pytest runtime/tests -q --disable-warnings --ignore="tools/voice_converter/.venv" 2>&1)
$PytestExit = $LASTEXITCODE

$PytestOutput | Set-Content -LiteralPath (Join-Path $ReportDir "pytest.txt") -Encoding UTF8

if ($PytestExit -eq 0) {
    $summary = ($PytestOutput | Select-Object -Last 1).ToString().Trim()
    Add-Gate "PYTEST" "PASS" "$summary"
} else {
    Add-Gate "PYTEST" "FAIL" "Échec de la suite de tests (voir pytest.txt)"
}

# ------------------------------------------------------------------------------
# ÉTAT GIT
# ------------------------------------------------------------------------------
if (Get-Command "git" -ErrorAction SilentlyContinue) {
    $status = @(& git status --porcelain=v1 2>&1)
    if ($status.Count -gt 0) {
        Add-Gate "GIT" "WARN" "$($status.Count) modifications non commitées"
    } else {
        Add-Gate "GIT" "PASS" "Working tree propre"
    }
}

# ------------------------------------------------------------------------------
# BILAN ET CERTIFICATION
# ------------------------------------------------------------------------------
$Duration = (Get-Date) - $Start
$Fails  = @($Results | Where-Object Status -eq "FAIL")
$Warns  = @($Results | Where-Object Status -eq "WARN")
$Passes = @($Results | Where-Object Status -eq "PASS")

$MandatoryGates = @("PROJECT","PYTHON","INVENTORY","RUFF","BYTECODE","PYTHON_AST","SQLITE","PYTEST")
$MissingGates   = @($MandatoryGates | Where-Object { $_ -notin $Results.Gate })

$Certified = ($Fails.Count -eq 0 -and $MissingGates.Count -eq 0)
$ReportPath = Join-Path $ReportDir "certification_report.json"

[PSCustomObject]@{
    Product         = "E-ZZIO"
    RunId           = $RunId
    DurationSeconds = [math]::Round($Duration.TotalSeconds, 3)
    Certified       = $Certified
    Passed          = $Passes.Count
    Failed          = $Fails.Count
    Warnings        = $Warns.Count
    Results         = $Results
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ReportPath -Encoding UTF8

Write-Host "`n==============================================================================" -ForegroundColor Cyan
if ($Certified) {
    Write-Host "`n                 E-ZZIO — 100% CERTIFIED" -ForegroundColor Green
    Write-Host "`n                 PASS     : $($Passes.Count)" -ForegroundColor Green
    Write-Host "                 FAIL     : 0" -ForegroundColor Green
    Write-Host "                 WARN     : $($Warns.Count)" -ForegroundColor Yellow
    Write-Host "                 STATUS   : PRÊT POUR LA PRODUCTION" -ForegroundColor Green
    Write-Host "`n                 RAPPORT  : $ReportPath`n" -ForegroundColor Gray
} else {
    Write-Host "`n                 E-ZZIO — NON CERTIFIÉ" -ForegroundColor Red
    Write-Host "`n                 PASS     : $($Passes.Count)" -ForegroundColor Green
    Write-Host "                 FAIL     : $($Fails.Count)" -ForegroundColor Red
    Write-Host "                 WARN     : $($Warns.Count)" -ForegroundColor Yellow
    Write-Host "                 STATUS   : FAIL-CLOSED / BLOCAGE" -ForegroundColor Red

    if ($Fails.Count -gt 0) {
        Write-Host "`n                 POINTS BLOQUANTS :" -ForegroundColor Red
        foreach ($f in $Fails) { Write-Host "                 - $($f.Gate) :: $($f.Message)" -ForegroundColor Red }
    }
    Write-Host "`n                 RAPPORT  : $ReportPath`n" -ForegroundColor Gray
}
Write-Host "==============================================================================`n" -ForegroundColor Cyan