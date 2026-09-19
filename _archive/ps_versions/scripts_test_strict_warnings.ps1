# E-ZZIO OS — TEST STRICT DES WARNINGS (DeprecationWarning)
Set-Location "G:\AI\E-zzio"
$PythonExe = ".\.venv\Scripts\python.exe"

Write-Host "[*] Exécution de pytest avec -W error::DeprecationWarning..." -ForegroundColor Cyan

# Flag correct pour Python 3.11 (DeprecationWarning, pas SyntaxWarning)
& $PythonExe -m pytest tests/ -v -W "error::DeprecationWarning" 2>&1 | Tee-Object -FilePath "runtime/audit/pytest_strict_warnings.txt"

$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "[OK] Aucun DeprecationWarning détecté." -ForegroundColor Green
} else {
    Write-Host "[FAIL] DeprecationWarning(s) détecté(s) — voir runtime/audit/pytest_strict_warnings.txt" -ForegroundColor Red
}

exit $exitCode
