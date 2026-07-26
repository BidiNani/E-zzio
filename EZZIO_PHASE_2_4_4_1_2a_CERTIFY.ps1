<#
.SYNOPSIS
    E-zzio Phase 2.4.4.1.2a: Ultimate Contract Certification & Safe Sealing
#>
[CmdletBinding()]
param([string]$ProjectRoot = "G:\AI\E-zzio")

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $ProjectRoot

function Write-Header { param([string]$Msg) Write-Host "`n=== $Msg ===" -ForegroundColor Cyan }
function Write-Success { param([string]$Msg) Write-Host "[+] $Msg" -ForegroundColor Green }
function Write-ErrorCustom { param([string]$Msg) Write-Host "[-] $Msg" -ForegroundColor Red }

Write-Header "E-ZZIO PHASE 2.4.4.1.2a : ULTIMATE CONTRACT CERTIFICATION"

# ==========================================
# 0. SAUVEGARDE MIROIR DE SÉCURITÉ
# ==========================================
$PrePurgeBackup = "G:\AI\E-zzio_PRE_PURGE_244"
if (!(Test-Path $PrePurgeBackup)) {
    New-Item -ItemType Directory -Force -Path $PrePurgeBackup | Out-Null
}
robocopy $ProjectRoot $PrePurgeBackup /MIR /XD .git __pycache__ node_modules | Out-Null
Write-Success "[+] Sauvegarde miroir de sécurité mise à jour."

# ==========================================
# 1. INTROSPECTION RÉELLE DES CONTRATS (CapabilityToken & TokenSigner)
# ==========================================
Write-Header "INSPECTION PROFONDE DES CONTRATS (Capability & Signer)"
& python -c "
import inspect
from runtime.contracts.capability import CapabilityToken, TokenSigner

print('=== CONTRACT INSPECTION ===')
print('CapabilityToken Signature:', inspect.signature(CapabilityToken))
print('CapabilityToken Source:')
print(inspect.getsource(CapabilityToken))
print('TokenSigner.sign Signature:', inspect.signature(TokenSigner.sign))
print('TokenSigner.verify Signature:', inspect.signature(TokenSigner.verify))
"

# ==========================================
# 2. COMPILATION ET SMOKE TEST CRYPTO ADAPTATIF
# ==========================================
Write-Header "COMPILATION BYTECODE (PYTHON COMPILEALL)"
& python -m compileall -q "runtime"
if ($LASTEXITCODE -ne 0) { throw "Erreur de compilation bytecode Python." }
Write-Success "[+] Compilation bytecode 100% OK."

Write-Header "EXÉCUTION DU SMOKE TEST CRYPTO ADAPTATIF"
$AdaptiveTestCode = @(
    "import inspect",
    "from runtime.contracts.capability import CapabilityToken, TokenSigner",
    "from runtime.kernel import Kernel",
    "",
    "print('=== EXÉCUTION DU TEST CRYPTO ===')",
    "token = CapabilityToken(subject='system', permissions=frozenset(['boot']))",
    "signer = TokenSigner()",
    "signature = signer.sign(token)",
    "assert signature is not None, 'SIGN FAILED'",
    "print('SIGN OK')",
    "",
    "verify_sig = inspect.signature(signer.verify)",
    "params = list(verify_sig.parameters.keys())",
    "print('VERIFY PARAMS:', params)",
    "",
    "if len(params) == 2:",
    "    result = signer.verify(token)",
    "elif len(params) == 3:",
    "    result = signer.verify(token, signature)",
    "else:",
    "    raise RuntimeError(f'Contrat verify inconnu: {verify_sig}')",
    "",
    "assert result is True, 'VERIFY FAILED'",
    "print('VERIFY OK')",
    "",
    "kernel = Kernel()",
    "print('Kernel type:', type(kernel))",
    "assert hasattr(kernel, 'key_manager') or hasattr(kernel, 'signer'), 'Kernel manquant de gestionnaire crypto'",
    "print('KERNEL CRYPTO PATH OK')"
) -join "`n"

& python -c $AdaptiveTestCode
if ($LASTEXITCODE -ne 0) { throw "Le smoke test adaptatif a échoué." }
Write-Success "[+] Smoke test adaptatif validé avec succès."

# ==========================================
# 3. INSPECTION VISIBLE DES DIFFS GITHUB / GIT
# ==========================================
Write-Header "INSPECTION DES DIFFS CRITIQUES AVANT COMMIT"
git diff --stat
Write-Host "`n--- DIFF: microkernel.py ---" -ForegroundColor Yellow
git diff -- runtime/core/microkernel.py
Write-Host "`n--- DIFF: capability.py ---" -ForegroundColor Yellow
git diff -- runtime/contracts/capability.py

Write-Host "`n[?] Souhaitez-vous valider le commit et l'étiquetage officiel ?" -ForegroundColor Yellow
$confirm = Read-Host "Valider le commit ? (Y/N)"
if ($confirm -ne "Y" -and $confirm -ne "y") {
    throw "Opération interrompue et annulée par l'opérateur."
}

# ==========================================
# 4. SCELLAGE TRANSACTIONNEL ET TAGAGE OFFICIEL V2.4.4
# ==========================================
Write-Header "SCELLAGE GIT TRANSACTIONNEL ET TAGAGE"
git add .
$GitChanges = git status --porcelain
if ([string]::IsNullOrWhiteSpace($GitChanges)) {
    Write-Host "[!] Aucun changement Git à commiter." -ForegroundColor Yellow
} else {
    git commit -m "E-zzio Runtime Phase 2.4.4.1.2a : Ultimate contract certification & certified kernel alignment" | Out-Null
    Write-Success "[+] Commit transactionnel validé."
}

$TagName = "v2.4.4-runtime-architectural-clean"
try {
    git rev-parse $TagName -- 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { git tag -d $TagName | Out-Null }
} catch {}

git tag $TagName
Write-Success "[+] Tag Git officiel apposé avec succès : $TagName"

Write-Header "MISSION ACCOMPLIE : E-ZZIO V2.4.4 CERTIFIÉ ET SCELLÉ"
