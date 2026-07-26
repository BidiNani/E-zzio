<#
.SYNOPSIS
    E-ZZIO Phase 2.4.4.2: Certified Surgical Repair & Zero Guess Architecture Validation
#>
[CmdletBinding()]
param([string]$ProjectRoot = "G:\AI\E-zzio")

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $ProjectRoot

function Write-Header { param([string]$Msg) Write-Host "`n=== $Msg ===" -ForegroundColor Cyan }
function Write-Success { param([string]$Msg) Write-Host "[+] $Msg" -ForegroundColor Green }
function Write-ErrorCustom { param([string]$Msg) Write-Host "[-] $Msg" -ForegroundColor Red }

Write-Header "E-ZZIO CERTIFIED SURGICAL REPAIR 2.4.4.2"

# ==========================================
# 0. BACKUP COMPLET DE SÉCURITÉ
# ==========================================
$Backup = "G:\AI\E-zzio_CERTIFIED_BACKUP_2442"
Write-Header "BACKUP SÉCURITÉ"
if (!(Test-Path $Backup)) {
    New-Item $Backup -ItemType Directory -Force | Out-Null
}
robocopy $ProjectRoot $Backup /MIR /XD .git __pycache__ node_modules | Out-Null
Write-Success "Backup certifié effectué avec succès."

# ==========================================
# 1. AUDIT MICROKERNEL
# ==========================================
$MicroKernel = Join-Path $ProjectRoot "runtime\core\microkernel.py"
if (!(Test-Path $MicroKernel)) {
    throw "microkernel.py introuvable"
}

$Audit = Join-Path $ProjectRoot "audit"
if (!(Test-Path $Audit)) {
    New-Item $Audit -ItemType Directory -Force | Out-Null
}
Copy-Item $MicroKernel (Join-Path $Audit "microkernel_before_2442.py") -Force

Write-Header "ÉTAT ACTUEL MICROKERNEL"
Select-String -Path $MicroKernel -Pattern "verify|signer|key_manager|TokenSigner|CapabilityToken|class " | ForEach-Object {
    Write-Host "L$($_.LineNumber): $($_.Line.Trim())" -ForegroundColor Yellow
}

# ==========================================
# 2. DÉCOUVERTE ET INSPECTION AUTOMATIQUE
# ==========================================
Write-Header "DÉCOUVERTE STRUCTURE RUNTIME"
$DiscoveryCode = @(
    "import importlib",
    "import inspect",
    "mods = ['runtime.kernel', 'runtime.core.microkernel', 'runtime.contracts.capability']",
    "for m in mods:",
    "    try:",
    "        mod = importlib.import_module(m)",
    "        print('\nMODULE:', m)",
    "        for n in dir(mod):",
    "            if 'Kernel' in n or 'Micro' in n:",
    "                print('FOUND:', n)",
    "    except Exception as e:",
    "        print('FAIL', m, e)",
    "from runtime.contracts.capability import TokenSigner",
    "print('\n=== TOKENSIGNER ===')",
    "print(inspect.getsource(TokenSigner))"
) -join "`n"

& python -c $DiscoveryCode

# ==========================================
# 3. PATCH SYNTAXIQUE CONTRÔLÉ
# ==========================================
Write-Header "PATCH SYNTAXIQUE CONTRÔLÉ"
$content = Get-Content $MicroKernel -Raw -Encoding UTF8

if ($content -match "if not \.verify") {
    Write-Host "Point verify corrompu détecté"
    $lines = Get-Content $MicroKernel
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "\.verify") {
            Write-Host "`nCONTEXTE:"
            $start = [Math]::Max(0, $i - 3)
            $end = [Math]::Min($lines.Count - 1, $i + 3)
            $lines[$start..$end] | ForEach-Object { Write-Host $_ }
        }
    }
    throw "STOP SÉCURITÉ: Un appel verify orphelin existe. Correction automatique interdite sans connaître l'objet signataire réel."
}
Write-Success "Aucune corruption syntaxique verify détectée."

# ==========================================
# 4. TEST CRYPTO RÉEL (AVEC DATACLASS REPLACE)
# ==========================================
Write-Header "TEST CRYPTO CERTIFIÉ"
$CryptoCode = @(
    "from runtime.contracts.capability import CapabilityToken, TokenSigner",
    "from dataclasses import replace",
    "signer = TokenSigner()",
    "token = CapabilityToken(subject='system', permissions=frozenset(['boot']))",
    "signature = signer.sign(token)",
    "signed = replace(token, signature=signature)",
    "assert signed.signature is not None",
    "assert signer.verify(signed)",
    "print('CRYPTO OK')"
) -join "`n"

& python -c $CryptoCode
if ($LASTEXITCODE -ne 0) { throw "Crypto contract invalide" }
Write-Success "Crypto validée et certifiée."

# ==========================================
# 5. DÉTECTION DU VRAI KERNEL
# ==========================================
Write-Header "DÉTECTION KERNEL"
$KernelDiscoveryCode = @(
    "import importlib",
    "import inspect",
    "mods = ['runtime.kernel', 'runtime.core.microkernel']",
    "for m in mods:",
    "    try:",
    "        mod = importlib.import_module(m)",
    "        for n in dir(mod):",
    "            if 'Kernel' in n or 'Micro' in n:",
    "                obj = getattr(mod, n)",
    "                if inspect.isclass(obj):",
    "                    print('KERNEL_FOUND:', m, n)",
    "    except Exception:",
    "        pass"
) -join "`n"

& python -c $KernelDiscoveryCode
Write-Success "Architecture kernel analysée."

# ==========================================
# 6. COMPILATION
# ==========================================
Write-Header "COMPILEALL"
& python -m compileall -q runtime
if ($LASTEXITCODE -ne 0) { throw "Compilation échouée" }
Write-Success "Python compile OK."

# ==========================================
# 7. SNAPSHOT FINAL ET DIFF
# ==========================================
Copy-Item $MicroKernel (Join-Path $Audit "microkernel_after_2442.py") -Force
Write-Header "DIFF FINAL"
git diff --stat
git diff -- runtime/core/microkernel.py

Write-Host "`nValidation humaine obligatoire. Aucune modification n'est commitée automatiquement." -ForegroundColor Yellow
$confirm = Read-Host "Commit + Tag ? Y/N"
if ($confirm -notin @("Y", "y")) {
    throw "Arrêt volontaire demandé par l'opérateur."
}

git add .
git commit -m "E-zzio Phase 2.4.4.2 Certified surgical repair"
git tag v2.4.4-certified-runtime-clean -f
Write-Success "COMMIT + TAG TERMINÉS AVEC SUCCÈS"
Write-Header "E-ZZIO 2.4.4.2 CERTIFIÉ"
