Set-Location "G:\AI\E-zzio"
$Python = 'G:\Python312\python.exe'

$tests = @(
    "test_v421.py",
    "test_boot_lifecycle.py",
    "test_v423_failures.py",
    "test_v424_adversarial.py",
    "test_v425_stale_recovery.py",
    "test_v44_incident_governance.py"
)

foreach ($t in $tests) {
    Write-Host "`n>>> Running $t" -ForegroundColor Yellow
    
    # ISOLATION : Purge impérative du lock avant chaque test pour éviter toute contamination inter-tests
    Remove-Item -Path "runtime\kernel\boot.lock" -Force -ErrorAction SilentlyContinue
    
    & $Python $t
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Test failed: $t"
        exit 1
    }
}
Write-Host "`n===============================================" -ForegroundColor Green
Write-Host " FULL V4 CERTIFICATION SUITE PASSED SUCCESSFULLY" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green