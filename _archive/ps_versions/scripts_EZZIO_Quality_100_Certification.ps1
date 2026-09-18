[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
<#
  E-ZZIO — QUALITY 100% CERTIFICATION (READ-ONLY)
  Principes : BUILD LAST — INTEGRATE FIRST + FAIL-CLOSED + READ-ONLY + ZERO FALSE POSITIVE
#>

Set-Location "G:\AI\E-zzio"
$PythonExe = ".\.venv\Scripts\python.exe"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$AuditDir  = "runtime/audit/quality_100_$Timestamp"
New-Item -ItemType Directory -Path $AuditDir -Force | Out-Null

Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "   E-ZZIO — QUALITY 100% CERTIFICATION (READ-ONLY)   " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

$certOk = $false
$blockingFailures = @()

# ---------------------------------------------------------------------------
# 0. SNAPSHOT FORENSIC GIT
# ---------------------------------------------------------------------------
Write-Host "`n[0] Snapshot forensic git (avant contrôle)..." -ForegroundColor Cyan
try {
    & git status --porcelain > "$AuditDir/git_status_before.txt" 2>&1
    & git diff --stat > "$AuditDir/git_diff_stat_before.txt" 2>&1
    Write-Host "  [OK] Snapshot git écrit dans $AuditDir" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] git indisponible ou dépôt non initialisé." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 1. RUFF — MODE STRICT, SANS --fix
# ---------------------------------------------------------------------------
Write-Host "`n[1] Ruff — contrôle strict (aucune correction automatique)..." -ForegroundColor Cyan

$ruffOutput = & $PythonExe -m ruff check core/ runtime/core/ routers/ interfaces/ tests/ 2>&1
$ruffExitCode = $LASTEXITCODE
$ruffOutput | Out-File "$AuditDir/ruff_strict.txt" -Encoding utf8
$ruffFindings = ($ruffOutput | Select-String -Pattern "^core/|^runtime/|^routers/|^interfaces/|^tests/").Count

Write-Host "  Exit code Ruff       : $ruffExitCode" -ForegroundColor $(if ($ruffExitCode -eq 0) { "Green" } else { "Red" })
Write-Host "  Findings Ruff        : $ruffFindings" -ForegroundColor $(if ($ruffFindings -eq 0) { "Green" } else { "Red" })

if ($ruffExitCode -ne 0 -or $ruffFindings -ne 0) {
    $blockingFailures += "Ruff : exit code $ruffExitCode, $ruffFindings finding(s) restant(s)"
}

# ---------------------------------------------------------------------------
# 2. COMPILATION BYTECODE COMPLÈTE
# ---------------------------------------------------------------------------
Write-Host "`n[2] Compilation bytecode complète..." -ForegroundColor Cyan

$compileOutput = & $PythonExe -m compileall -q core runtime routers interfaces tests 2>&1
$compileExitCode = $LASTEXITCODE
$compileOutput | Out-File "$AuditDir/compileall.txt" -Encoding utf8

Write-Host "  Exit code compileall : $compileExitCode" -ForegroundColor $(if ($compileExitCode -eq 0) { "Green" } else { "Red" })
if ($compileExitCode -ne 0) {
    $blockingFailures += "compileall : exit code $compileExitCode"
}

# ---------------------------------------------------------------------------
# 3. QUALITY GATE INDÉPENDANT
# ---------------------------------------------------------------------------
Write-Host "`n[3] Quality Gate indépendant..." -ForegroundColor Cyan

if (Test-Path "scripts/quality_gate.py") {
    & $PythonExe scripts/quality_gate.py 2>&1 | Tee-Object -FilePath "$AuditDir/quality_gate.txt"
    $qgExitCode = $LASTEXITCODE
    Write-Host "  Exit code quality_gate.py : $qgExitCode" -ForegroundColor $(if ($qgExitCode -eq 0) { "Green" } else { "Red" })
    if ($qgExitCode -ne 0) {
        $blockingFailures += "quality_gate.py : exit code $qgExitCode"
    }
} else {
    $blockingFailures += "scripts/quality_gate.py introuvable"
    Write-Host "  [FAIL] scripts/quality_gate.py introuvable." -ForegroundColor Red
}

# ---------------------------------------------------------------------------
# 4. PYTEST — COMPTAGE AUTO-COHÉRENT VIA JUNIT XML
# ---------------------------------------------------------------------------
Write-Host "`n[4] Pytest — suite complète, comptage auto-cohérent..." -ForegroundColor Cyan

$junitPath = "$AuditDir/junit.xml"

# 4a. Comptage indépendant des tests collectés
$collectOutput = & $PythonExe -m pytest --collect-only -q tests 2>&1
$collectOutput | Out-File "$AuditDir/pytest_collect_only.txt" -Encoding utf8
$collectedCount = 0
$collectLine = $collectOutput | Select-String -Pattern "(\d+)\s+tests?\s+collected" | Select-Object -Last 1
if ($collectLine -and $collectLine.Line -match "(\d+)\s+tests?\s+collected") {
    $collectedCount = [int]$Matches[1]
}
Write-Host "  Tests collectés (référence) : $collectedCount" -ForegroundColor Cyan

# 4b. Exécution réelle avec rapport JUnit XML
& $PythonExe -m pytest tests -q --junitxml="$junitPath" 2>&1 | Tee-Object -FilePath "$AuditDir/pytest_run.txt"
$pytestExitCode = $LASTEXITCODE

$testsRun = -1
$failures = -1
$errors = -1
$skipped = -1

if (Test-Path $junitPath) {
    [xml]$junit = Get-Content $junitPath
    $suite = $null
    if ($junit.testsuites -and $junit.testsuites.testsuite) {
        $suite = $junit.testsuites.testsuite
        if ($suite -is [System.Array]) { $suite = $suite[0] }
    } elseif ($junit.testsuite) {
        $suite = $junit.testsuite
    }

    if ($suite) {
        $testsRun = [int]$suite.tests
        $failures = [int]$suite.failures
        $errors   = [int]$suite.errors
        $skipped  = [int]$suite.skipped
    } else {
        $blockingFailures += "junit.xml présent mais aucune <testsuite> trouvée"
    }
} else {
    $blockingFailures += "junit.xml non généré"
}

# 4c. xfail/xpass
$xfailedCount = 0
$xpassedCount = 0
$runText = Get-Content "$AuditDir/pytest_run.txt" -Raw
if ($runText -match "(\d+)\s+xfailed") { $xfailedCount = [int]$Matches[1] }
if ($runText -match "(\d+)\s+xpassed") { $xpassedCount = [int]$Matches[1] }

Write-Host "  Exit code pytest     : $pytestExitCode" -ForegroundColor $(if ($pytestExitCode -eq 0) { "Green" } else { "Red" })
Write-Host "  tests (JUnit)        : $testsRun" -ForegroundColor Cyan
Write-Host "  failures             : $failures" -ForegroundColor $(if ($failures -eq 0) { "Green" } else { "Red" })
Write-Host "  errors               : $errors" -ForegroundColor $(if ($errors -eq 0) { "Green" } else { "Red" })
Write-Host "  skipped              : $skipped" -ForegroundColor $(if ($skipped -eq 0) { "Green" } else { "Red" })
Write-Host "  xfailed              : $xfailedCount" -ForegroundColor $(if ($xfailedCount -eq 0) { "Green" } else { "Red" })
Write-Host "  xpassed              : $xpassedCount" -ForegroundColor $(if ($xpassedCount -eq 0) { "Green" } else { "Red" })

# 4d. Conditions strictes
if ($pytestExitCode -ne 0)            { $blockingFailures += "pytest exit code = $pytestExitCode" }
if ($testsRun -le 0)                  { $blockingFailures += "aucun test exécuté (tests=$testsRun)" }
if ($testsRun -ne $collectedCount)    { $blockingFailures += "incohérence : $testsRun exécutés vs $collectedCount collectés" }
if ($failures -ne 0)                  { $blockingFailures += "$failures échec(s)" }
if ($errors -ne 0)                    { $blockingFailures += "$errors erreur(s)" }
if ($skipped -ne 0)                   { $blockingFailures += "$skipped test(s) ignoré(s)" }
if ($xfailedCount -ne 0)              { $blockingFailures += "$xfailedCount xfail détecté(s)" }
if ($xpassedCount -ne 0)              { $blockingFailures += "$xpassedCount xpass détecté(s)" }

# ---------------------------------------------------------------------------
# 5. SNAPSHOT FORENSIC APRÈS CONTRÔLE
# ---------------------------------------------------------------------------
Write-Host "`n[5] Snapshot forensic git (après contrôle)..." -ForegroundColor Cyan
try {
    & git status --porcelain > "$AuditDir/git_status_after.txt" 2>&1
    $diffBeforeAfter = Compare-Object (Get-Content "$AuditDir/git_status_before.txt") (Get-Content "$AuditDir/git_status_after.txt")
    if ($diffBeforeAfter) {
        $blockingFailures += "Le script a modifié l'arbre git (non read-only)"
        Write-Host "  [FAIL] Le contrôle n'était pas read-only." -ForegroundColor Red
    } else {
        Write-Host "  [OK] Aucun changement git détecté." -ForegroundColor Green
    }
} catch {
    Write-Host "  [WARN] Comparaison git avant/après impossible." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# 6. VERDICT
# ---------------------------------------------------------------------------
Write-Host "`n=====================================================" -ForegroundColor Cyan
Write-Host "   VERDICT QUALITY 100%                               " -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

$certOk = ($blockingFailures.Count -eq 0)

if ($certOk) {
    Write-Host "  STATUT : QUALITY 100% CERTIFIÉE" -ForegroundColor Green
    Write-Host "  Ruff 0/0, pytest $testsRun/$testsRun (0 failures, 0 errors, 0 skipped, 0 xfail), exit codes = 0, contrôle read-only confirmé." -ForegroundColor Green
} else {
    Write-Host "  STATUT : NON CERTIFIÉ — $($blockingFailures.Count) raison(s) bloquante(s)" -ForegroundColor Red
    foreach ($reason in $blockingFailures) {
        Write-Host "    - $reason" -ForegroundColor Red
    }
}

# CI_SUMMARY
Write-Host "`n[CI_SUMMARY]" -ForegroundColor Cyan
Write-Host "  ruff_findings=$ruffFindings" -ForegroundColor Cyan
Write-Host "  compile_exit=$compileExitCode" -ForegroundColor Cyan
Write-Host "  pytest_exit=$pytestExitCode" -ForegroundColor Cyan
Write-Host "  tests_run=$testsRun" -ForegroundColor Cyan
Write-Host "  failures=$failures" -ForegroundColor Cyan
Write-Host "  errors=$errors" -ForegroundColor Cyan
Write-Host "  skipped=$skipped" -ForegroundColor Cyan
Write-Host "  cert_ok=$(if ($certOk) { 'true' } else { 'false' })" -ForegroundColor Cyan

Write-Host "`n  Rapports complets : $AuditDir" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

if (-not $certOk) { exit 1 } else { exit 0 }