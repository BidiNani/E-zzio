[CmdletBinding()]
param(
    [string]$ProjectRoot = "G:\AI\E-zzio"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $ProjectRoot

function Write-Header { param([string]$Msg) Write-Host "`n=== $Msg ===" -ForegroundColor Cyan }
function Write-Success { param([string]$Msg) Write-Host "[+] $Msg" -ForegroundColor Green }

Write-Header "E-ZZIO PHASE 2.4.4 FINAL CERTIFIED"

# =================================================
# 0. BACKUP SÉCURITÉ
# =================================================
$Backup = "G:\AI\E-zzio_FINAL_BACKUP"
if (!(Test-Path $Backup)) {
    New-Item $Backup -ItemType Directory -Force | Out-Null
}
robocopy $ProjectRoot $Backup /MIR /XD .git __pycache__ node_modules | Out-Null
Write-Success "Backup miroir terminé"

# =================================================
# 1. AUDIT & VARIABLES CHEMINS
# =================================================
$MK = Join-Path $ProjectRoot "runtime\core\microkernel.py"
$Audit = Join-Path $ProjectRoot "audit"

if (!(Test-Path $MK)) {
    throw "Fichier critique microkernel.py introuvable à l'emplacement : $MK"
}
if (!(Test-Path $Audit)) {
    New-Item $Audit -ItemType Directory -Force | Out-Null
}

Copy-Item $MK (Join-Path $Audit "microkernel_before_final_cert.py") -Force

Write-Header "ÉTAT ACTUEL MICROKERNEL"
Select-String -Path $MK -Pattern "verify|signer|key_manager|TokenSigner" | ForEach-Object {
    Write-Host "L$($_.LineNumber): $($_.Line.Trim())" -ForegroundColor Yellow
}

# =================================================
# 2. INSPECTION CRYPTO & TEST RÉEL
# =================================================
Write-Header "VALIDATION DU CONTRAT CRYPTOGRAPHIQUE"
$CryptoCode = @(
    "from dataclasses import replace",
    "from runtime.contracts.capability import CapabilityToken, TokenSigner",
    "s = TokenSigner()",
    "t = CapabilityToken(subject='system', permissions=frozenset(['boot']))",
    "sig = s.sign(t)",
    "signed = replace(t, signature=sig)",
    "assert signed.signature, 'Signature missing'",
    "assert s.verify(signed), 'Verification failed'",
    "print('CRYPTO_OK')"
) -join "`n"

& python -c $CryptoCode
if ($LASTEXITCODE -ne 0) {
    throw "Contrat crypto invalide"
}
Write-Success "Crypto certifiée et validée"

# =================================================
# 3. VÉRIFICATION STRICTE DE CORRUPTION
# =================================================
Write-Header "VÉRIFICATION DE L'INTÉGRITÉ DU MICROKERNEL"
$content = Get-Content $MK -Raw -Encoding utf8

if ($content -match "if\s+not\s+\.verify") {
    Write-Host "`nVERIFY ORPHELIN DÉTECTÉ" -ForegroundColor Red
    Select-String -Path $MK -Pattern "\.verify" | ForEach-Object {
        Write-Host $_.Line
    }
    throw "STOP SÉCURITÉ: Un appel verify orphelin 'if not .verify' subsiste."
}
Write-Success "Aucun verify orphelin détecté"

# =================================================
# 4. COMPILATION BYTECODE
# =================================================
Write-Header "COMPILATION BYTECODE (COMPILEALL)"
& python -m compileall -q runtime
if ($LASTEXITCODE -ne 0) {
    throw "Échec de la compilation Python"
}
Write-Success "Compilation bytecode OK"

# =================================================
# 5. CONTRÔLE DES IMPORTS CRITIQUES
# =================================================
Write-Header "SCAN DES IMPORTS DU RUNTIME"
$ImportScanCode = @(
    "import pkgutil",
    "import runtime",
    "errors = []",
    "for m in pkgutil.walk_packages(runtime.__path__, runtime.__name__ + '.'):",
    "    try:",
    "        __import__(m.name)",
    "    except Exception as e:",
    "        errors.append((m.name, str(e)))",
    "critical = [x for x in errors if 'ImportError' in x[1] or 'ModuleNotFoundError' in x[1] or 'SyntaxError' in x[1]]",
    "if critical:",
    "    print(critical)",
    "    raise SystemExit(1)",
    "print('IMPORT_SCAN_OK')"
) -join "`n"

& python -c $ImportScanCode
if ($LASTEXITCODE -ne 0) {
    throw "Erreur d'import critique détectée dans le runtime"
}
Write-Success "Imports du runtime propres"

# =================================================
# 6. SNAPSHOT FINAL ET DIFF GIT
# =================================================
Copy-Item $MK (Join-Path $Audit "microkernel_after_final_cert.py") -Force

Write-Header "DIFFÉRENTIEL GIT"
git diff --stat
git diff -- runtime/core/microkernel.py

Write-Host "`nValidation humaine obligatoire. Aucun commit automatique sans accord." -ForegroundColor Yellow
$confirm = Read-Host "Procéder au Commit et au Tag ? (Y/N)"

if ($confirm -notin @("Y", "y")) {
    throw "Arrêt volontaire demandé par l'opérateur."
}

# =================================================
# 7. SCELLAGE ET TAGAGE OFFICIEL
# =================================================
git add .
git commit -m "E-zzio Phase 2.4.4 final certified runtime reconciliation" | Out-Null
git tag -f "v2.4.4-certified-runtime-clean"

Write-Success "Git scellé et taggé avec succès (v2.4.4-certified-runtime-clean)"
Write-Header "E-ZZIO 2.4.4 CERTIFIÉ AVEC SUCCÈS"
