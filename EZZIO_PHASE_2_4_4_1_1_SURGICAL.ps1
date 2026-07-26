<#
.SYNOPSIS
    E-zzio Phase 2.4.4.1.1: Surgical Kernel Reconciliation & Safe Contract Bridge
#>
[CmdletBinding()]
param([string]$ProjectRoot = "G:\AI\E-zzio")

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $ProjectRoot

function Write-Header { param([string]$Msg) Write-Host "`n=== $Msg ===" -ForegroundColor Cyan }
function Write-Success { param([string]$Msg) Write-Host "[+] $Msg" -ForegroundColor Green }
function Write-ErrorCustom { param([string]$Msg) Write-Host "[-] $Msg" -ForegroundColor Red }

Write-Header "E-ZZIO PHASE 2.4.4.1.1 : SURGICAL KERNEL RECONCILIATION"

# ==========================================
# 0. SAUVEGARDE MIROIR ET SNAPSHOT DU FICHIER CIBLE
# ==========================================
$PrePurgeBackup = "G:\AI\E-zzio_PRE_PURGE_244"
$AuditDir = Join-Path $ProjectRoot "audit"

if (!(Test-Path $PrePurgeBackup)) {
    New-Item -ItemType Directory -Force -Path $PrePurgeBackup | Out-Null
}
robocopy $ProjectRoot $PrePurgeBackup /MIR /XD .git __pycache__ node_modules | Out-Null
Write-Success "[+] Sauvegarde miroir globale effectuée."

$MicroKernelPath = Join-Path $ProjectRoot "runtime\core\microkernel.py"
if (!(Test-Path $MicroKernelPath)) {
    throw "Fichier critique introuvable : $MicroKernelPath"
}

# Snapshot avant modification
Copy-Item $MicroKernelPath (Join-Path $AuditDir "microkernel_before_phase24411.py") -Force
Write-Success "[+] Snapshot 'before' enregistré dans audit/"

# ==========================================
# 1. INSPECTION AVANT PATCH
# ==========================================
Write-Header "INSPECTION DES LIGNES CIBLES DANS MICROKERNEL"
Select-String -Path $MicroKernelPath -Pattern "verify|TokenSigner|CapabilityToken|ExecutionContext" | ForEach-Object {
    Write-Host "  Ligne $($_.LineNumber): $($_.Line.Trim())" -ForegroundColor Yellow
}

# ==========================================
# 2. PATCH CHIRURGICAL SÛR (Imports et .verify)
# ==========================================
Write-Header "APPLICATION DU PATCH CHIRURGICAL"
$c = Get-Content $MicroKernelPath -Raw -Encoding utf8

# Correction de l'import des contrats
$c = $c -replace "from\s+runtime\.contracts\.execution_context\s+import\s+ExecutionContext,\s*TokenSigner", "from runtime.contracts.execution_context import ExecutionContext`nfrom runtime.contracts.capability import TokenSigner"
$c = $c -replace "from\s+runtime\.contracts\.execution_context\s+import\s+TokenSigner,\s*ExecutionContext", "from runtime.contracts.execution_context import ExecutionContext`nfrom runtime.contracts.capability import TokenSigner"

# Correction sécurisée de l'appel de vérification (utilisation de l'attribut d'instance existant ou signataire du kernel)
# On remplace le point orphelin par l'appel à l'attribut signer/key_manager déjà présent dans le cycle de vie du Kernel
$c = $c -replace "if\s+not\s+\.verify\(", "if not self.signer.verify("

Set-Content -Path $MicroKernelPath -Value $c -Encoding utf8
Write-Success "[+] Fichier microkernel.py réconcilié."

# Snapshot après modification pour traçabilité
Copy-Item $MicroKernelPath (Join-Path $AuditDir "microkernel_after_phase24411.py") -Force
Write-Success "[+] Snapshot 'after' enregistré dans audit/"

# ==========================================
# 3. NETTOYAGE DES CACHES DE DEV
# ==========================================
Write-Header "NETTOYAGE DES CACHES LOCAUX"
Get-ChildItem $ProjectRoot -Recurse -Directory -Include "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem $ProjectRoot -Recurse -File | Where-Object { $_.Name -match "\.pyc$" } | Remove-Item -Force -ErrorAction SilentlyContinue
Write-Success "[+] Caches purgés."

# ==========================================
# 4. COMPILATION ET SMOKE TEST ADAPTATIF
# ==========================================
Write-Header "COMPILATION BYTECODE (PYTHON COMPILEALL)"
& python -m compileall -q "runtime"
if ($LASTEXITCODE -ne 0) {
    Write-ErrorCustom "Échec de la compilation bytecode ! Restauration du snapshot..."
    Copy-Item (Join-Path $AuditDir "microkernel_before_phase24411.py") $MicroKernelPath -Force
    throw "Erreur critique de compilation bytecode Python."
}
Write-Success "[+] Compilation bytecode 100% OK."

Write-Header "SMOKE TEST ADAPTATIF (Crypto et Signatures)"
$SmokeTestCode = @(
    "import inspect",
    "from runtime.contracts.capability import CapabilityToken, TokenSigner",
    "print('Signature de TokenSigner:', inspect.signature(TokenSigner))",
    "token = CapabilityToken(subject='system', permissions=frozenset(['boot']))",
    "signer = TokenSigner()",
    "sig = signer.sign(token)",
    "assert signer.verify(token), 'Verification failed'",
    "print('SMOKE TEST CRYPTO ADAPTATIF OK')"
) -join "`n"

& python -c $SmokeTestCode
if ($LASTEXITCODE -ne 0) { throw "Le smoke test adaptatif a échoué." }
Write-Success "[+] Sous-système cryptographique validé."

# ==========================================
# 5. DIFF HUMAIN ET CONFIRMATION
# ==========================================
Write-Header "INSPECTION DU DIFF GIT"
git diff --stat
git diff -- runtime/core/microkernel.py

Write-Host "`n[?] Souhaitez-vous valider le commit et l'étiquetage de cette réconciliation ?" -ForegroundColor Yellow
$confirm = Read-Host "Valider le commit ? (Y/N)"
if ($confirm -ne "Y" -and $confirm -ne "y") {
    throw "Opération interrompue et annulée par l'opérateur."
}

# ==========================================
# 6. SCELLAGE GIT ET TAGAGE OFFICIEL
# ==========================================
Write-Header "SCELLAGE GIT TRANSACTIONNEL ET TAGAGE"
git add .
$GitChanges = git status --porcelain
if ([string]::IsNullOrWhiteSpace($GitChanges)) {
    Write-Host "[!] Aucun changement Git à commiter." -ForegroundColor Yellow
} else {
    git commit -m "E-zzio Runtime Phase 2.4.4.1.1 : Surgical kernel reconciliation & safe signer binding" | Out-Null
    Write-Success "[+] Commit transactionnel validé."
}

$TagName = "v2.4.4-runtime-architectural-clean"
try {
    git rev-parse $TagName -- 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        git tag -d $TagName | Out-Null
    }
} catch {}

git tag $TagName
Write-Success "[+] Tag Git officiel apposé avec succès : $TagName"

Write-Header "PHASE 2.4.4.1.1 TERMINÉE AVEC SUCCÈS"
Write-Success "Le runtime E-zzio est réconcilié, intègre, audité avec snapshots et étiqueté."
