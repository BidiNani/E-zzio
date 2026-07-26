<#
.SYNOPSIS
    E-ZZIO Phase 2.4.4: Final Certification & Zero Guess Architecture Validation
#>
[CmdletBinding()]
param([string]$ProjectRoot = "G:\AI\E-zzio")

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $ProjectRoot

function Write-Header { param([string]$Msg) Write-Host "`n=== $Msg ===" -ForegroundColor Cyan }
function Write-Success { param([string]$Msg) Write-Host "[+] $Msg" -ForegroundColor Green }
function Write-ErrorCustom { param([string]$Msg) Write-Host "[-] $Msg" -ForegroundColor Red }

Write-Header "E-ZZIO PHASE 2.4.4 FINAL CERTIFICATION"

# =====================================================
# 0. BACKUP SÉCURITÉ
# =====================================================
$Backup = "G:\AI\E-zzio_CERTIFICATION_BACKUP"
Write-Header "BACKUP SÉCURITÉ"
if (!(Test-Path $Backup)) {
    New-Item $Backup -ItemType Directory | Out-Null
}
robocopy $ProjectRoot $Backup /MIR /XD .git __pycache__ node_modules | Out-Null
Write-Success "Backup sécurité créé"

# =====================================================
# 1. SNAPSHOT MICROKERNEL
# =====================================================
$MicroKernel = Join-Path $ProjectRoot "runtime\core\microkernel.py"
$Audit = Join-Path $ProjectRoot "audit"
if (!(Test-Path $Audit)) {
    New-Item $Audit -ItemType Directory -Force | Out-Null
}
Copy-Item $MicroKernel (Join-Path $Audit "microkernel_before_certification.py") -Force
Write-Success "Snapshot microkernel enregistré"

# =====================================================
# 2. INSPECTION ARCHITECTURE RÉELLE
# =====================================================
Write-Header "DETECTION ARCHITECTURE REELLE"
$DiscoveryCode = @(
    "import importlib",
    "import inspect",
    "modules = ['runtime.kernel', 'runtime.core.microkernel']",
    "for module_name in modules:",
    "    print('\nMODULE:', module_name)",
    "    try:",
    "        m = importlib.import_module(module_name)",
    "        for name, obj in vars(m).items():",
    "            if inspect.isclass(obj):",
    "                if 'Kernel' in name or 'Micro' in name:",
    "                    print('CLASS:', name)",
    "    except Exception as e:",
    "        print('IMPORT ERROR:', e)"
) -join "`n"

& python -c $DiscoveryCode

# =====================================================
# 3. VALIDATION DU CONTRAT CRYPTOGRAPHIQUE
# =====================================================
Write-Header "VALIDATION TOKEN SIGNER"
$CryptoCode = @(
    "from dataclasses import replace",
    "from runtime.contracts.capability import CapabilityToken, TokenSigner",
    "signer = TokenSigner()",
    "token = CapabilityToken(subject='system', permissions=frozenset(['boot']))",
    "signature = signer.sign(token)",
    "signed = replace(token, signature=signature)",
    "assert signed.signature is not None",
    "assert signer.verify(signed)",
    "print('CRYPTO CONTRACT OK')"
) -join "`n"

& python -c $CryptoCode
if ($LASTEXITCODE -ne 0) {
    throw "Erreur contrat cryptographique"
}
Write-Success "Crypto validée et certifiée"

# =====================================================
# 4. DÉTECTION DES VERIFY CORROMPUS OU ORPHELINS
# =====================================================
Write-Header "VERIFICATION MICROKERNEL"
$bad = Select-String -Path $MicroKernel -Pattern "if not \.verify"
if ($bad) {
    Write-Host "CORRUPTION DETECTEE:" -ForegroundColor Red
    $bad | ForEach-Object { Write-Host $_.Line }
    throw "Arrêt sécurité : microkernel contient encore un verify orphelin. Correction automatique refusée."
}
Write-Success "Aucun verify orphelin détecté"

# =====================================================
# 5. COMPILATION PYTHON GLOBALE DU RUNTIME
# =====================================================
Write-Header "COMPILEALL"
& python -m compileall -q runtime
if ($LASTEXITCODE -ne 0) {
    throw "Compilation Python échouée"
}
Write-Success "Compilation Python OK"

# =====================================================
# 6. SCAN DES IMPORTS DU RUNTIME (SANS ERREUR DE SYNTAXE BASH)
# =====================================================
Write-Header "SCAN IMPORT RUNTIME"
$ImportTestCode = @(
    "import pkgutil",
    "import runtime",
    "errors = []",
    "for m in pkgutil.walk_packages(runtime.__path__, runtime.__name__ + '.'):",
    "    try:",
    "        __import__(m.name)",
    "    except Exception as e:",
    "        errors.append((m.name, str(e)))",
    "if errors:",
    "    print(errors)",
    "    raise SystemExit(1)",
    "print('RUNTIME IMPORT SCAN OK')"
) -join "`n"

& python -c $ImportTestCode
if ($LASTEXITCODE -ne 0) {
    throw "Erreur import runtime"
}
Write-Success "Runtime import propre"

# =====================================================
# 7. SNAPSHOT FINAL, DIFF ET SCELLAGE SÉCURISÉ
# =====================================================
Copy-Item $MicroKernel (Join-Path $Audit "microkernel_after_certification.py") -Force
Write-Header "DIFF FINAL"
git diff --stat
git diff -- runtime/core/microkernel.py

Write-Host "`nValidation humaine obligatoire. Aucun commit automatique." -ForegroundColor Yellow
$confirm = Read-Host "Commit + Tag ? Y/N"
if ($confirm -notin @("Y", "y")) {
    throw "Arrêt volontaire demandé par l'opérateur."
}

git add .
git commit -m "E-zzio Phase 2.4.4 Final certification runtime architecture"
git tag -f "v2.4.4-certified-runtime-clean"
Write-Success "Git scellé et taggé avec succès"
Write-Header "E-ZZIO 2.4.4 CERTIFIÉ"
