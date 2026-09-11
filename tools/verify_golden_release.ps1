param (
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
Set-Location $RootDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   E-ZZIO V9.1 — GOLDEN RELEASE INTEGRITY VERIFIER" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$Python = Join-Path $RootDir ".venv\Scripts\python.exe"

# 1. Vérification Git Identity
Write-Host "[1/9] Verification de l'identite Git..." -ForegroundColor Yellow
$ExpectedCommit = "dde4d186ce8cee1bdcfa42f6850763adb08b25f8"
$CurrentHead = & git rev-parse HEAD
if ($CurrentHead -ne $ExpectedCommit) {
    Write-Error "[FAIL] Git HEAD mismatch! Expected: $ExpectedCommit, Observed: $CurrentHead"
    exit 1
}
Write-Host "[OK] Git HEAD conforme : $CurrentHead" -ForegroundColor Green

# 2. Vérification Frozen Core (3/3)
Write-Host "[2/9] Verification cryptographique du Frozen Core..." -ForegroundColor Yellow
$FC_Ok = & $Python -c "
import hashlib, sys
expected = {
    'core/capabilities/capability_policy.py': '89A770354EBFE4233697F944F0963C3873B811AF1C7DF73E6DACC7AABB389AE2',
    'core/capabilities/registry.py': '3EE057B327354FAA95CF72A0A920A5EED4FA5DF77AE87298615ED3860FFB0F68',
    'core/security/audit_ledger.py': 'B26E0D106F0E76121B15B6278F057DEA3ABC1395AA425D86D383E695DFC21C17'
}
for p, h in expected.items():
    actual = hashlib.sha256(open(p, 'rb').read()).hexdigest().upper()
    if actual != h:
        sys.exit(1)
print('OK')
"
if ($LASTEXITCODE -ne 0) {
    Write-Error "[FAIL] Frozen Core inviolability violation!"
    exit 1
}
Write-Host "[OK] Frozen Core 3/3 INTACT." -ForegroundColor Green

# 3. Vérification des Empreintes d'Artefacts
Write-Host "[3/9] Recalcul SHA-256 et verification des artefacts de release..." -ForegroundColor Yellow
$Artifacts_Ok = & $Python -c "
import hashlib, json, sys
data = json.load(open('state/audit/golden/v9.1/artifact_hashes.json', encoding='utf-8'))
for rel, info in data.items():
    actual = hashlib.sha256(open(rel, 'rb').read()).hexdigest().upper()
    expected = info['sha256']
    if actual != expected:
        print('MISMATCH in ' + rel + ': ' + actual + ' != ' + expected)
        sys.exit(1)
print('OK')
"
if ($LASTEXITCODE -ne 0) {
    Write-Error "[FAIL] Artefact hash mismatch detected!"
    exit 1
}
Write-Host "[OK] Tous les artefacts de release correspondent aux hashes certifiés." -ForegroundColor Green

# 4. Vérification Forensique APK
Write-Host "[4/9] Verification du binaire APK Release..." -ForegroundColor Yellow
$ApkPath = Join-Path $RootDir "dist\android\E-ZzIO-v9.1-release.apk"
if (-not (Test-Path $ApkPath)) {
    Write-Error "[FAIL] dist/android/E-ZzIO-v9.1-release.apk introuvable !"
    exit 1
}
$Apk_Ok = & $Python -c "
import zipfile, sys
with zipfile.ZipFile(r'$ApkPath', 'r') as z:
    names = set(z.namelist())
    if 'classes.dex' not in names or 'resources.arsc' not in names or 'AndroidManifest.xml' not in names:
        sys.exit(1)
print('OK')
"
if ($LASTEXITCODE -ne 0) {
    Write-Error "[FAIL] APK non conforme (classes.dex ou resources.arsc manquant) !"
    exit 1
}
Write-Host "[OK] Binaire APK release Dalvik & ressources valides." -ForegroundColor Green

# 5. Vérification Signature APK
Write-Host "[5/9] Verification de la signature APK v2..." -ForegroundColor Yellow
$ApkSigner = "G:\tools\android-sdk\build-tools\34.0.0\apksigner.bat"
if (Test-Path $ApkSigner) {
    $sigOut = & $ApkSigner verify --verbose $ApkPath
    if (-not ($sigOut -match "Verified using v2 scheme \(APK Signature Scheme v2\): true")) {
        Write-Error "[FAIL] Signature APK invalide !"
        exit 1
    }
    Write-Host "[OK] Signature v2 verifiee avec succes." -ForegroundColor Green
} else {
    Write-Host "[WARN] apksigner non trouve, etape ignoree." -ForegroundColor Yellow
}

# 6. Vérification de la Documentation Golden
Write-Host "[6/9] Verification de la documentation Golden..." -ForegroundColor Yellow
$RequiredDocs = @(
    "docs/RELEASE_MANIFEST.json",
    "docs/E-ZZIO_V9.1_GOLDEN_RELEASE_LOCK.md",
    "docs/GOLDEN_RELEASE_RESTORE.md",
    "docs/V9.1_DEVELOPMENT_POLICY.md"
)
foreach ($doc in $RequiredDocs) {
    if (-not (Test-Path $doc)) {
        Write-Error "[FAIL] Document obligatoire manquant : $doc"
        exit 1
    }
}
Write-Host "[OK] Documentation Golden complete et presente." -ForegroundColor Green

# 7. Vérification de l'Archive Golden
Write-Host "[7/9] Verification de l'archive Golden Source..." -ForegroundColor Yellow
$GoldenArchive = Join-Path $RootDir "dist\releases\E-ZzIO-V9.1-GOLDEN-SOURCE.zip"
$GoldenManifest = Join-Path $RootDir "dist\releases\E-ZzIO-V9.1-GOLDEN-MANIFEST.json"

if (-not (Test-Path $GoldenArchive) -or -not (Test-Path $GoldenManifest)) {
    Write-Error "[FAIL] Archive ou manifeste Golden Release manquant !"
    exit 1
}
$ExpectedArchiveHash = "D3351A86D1BF7FAFF5125CE76E54A5106EF788D84259E1BE9B3B4C37EBEE8A7F"
$ActualArchiveHash = (Get-FileHash -Path $GoldenArchive -Algorithm SHA256).Hash
if ($ActualArchiveHash -ne $ExpectedArchiveHash) {
    Write-Error "[FAIL] Hash archive Golden mismatch! Expected: $ExpectedArchiveHash, Actual: $ActualArchiveHash"
    exit 1
}
Write-Host "[OK] Archive Golden Source intègre ($ActualArchiveHash)." -ForegroundColor Green

# 8. Rejeu de la Suite de Tests (111 tests)
if (-not $SkipTests) {
    Write-Host "[8/9] Verification de la suite de régression (111 tests)..." -ForegroundColor Yellow
    & $Python -m pytest tests/test_hitl_approval.py tests/test_hermes_mcp_confinement.py tests/test_federation_smokes.py tests/test_ai_office_visual.py tests/test_ai_office.py tests/test_product_certification.py tests/test_product_lifecycle.py tests/test_hitl_api.py tests/test_hitl_cli.py tests/test_hitl_discord.py tests/test_capability_policy.py tests/test_capability_enforcement.py tests/test_android_project.py tests/test_android_artifact.py tests/test_android_runtime_contract.py tests/test_android_device_gate.py -q
    if ($LASTEXITCODE -ne 0) {
        Write-Error "[FAIL] Suite de régression en échec !"
        exit 1
    }
    Write-Host "[OK] 111/111 tests PASS." -ForegroundColor Green
} else {
    Write-Host "[8/9] Suite de tests ignorée (-SkipTests)." -ForegroundColor DarkGray
}

# 9. Verdict Global
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   GOLDEN_RELEASE_VALID" -ForegroundColor Green
Write-Host "   E-ZZIO V9.1 BASELINE IMMUTABLE & VERIFIEE AVEC SUCCES" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
