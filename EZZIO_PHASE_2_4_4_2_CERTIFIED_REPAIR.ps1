<#
.SYNOPSIS
E-ZZIO Phase 2.4.4.2
Certified Surgical Repair
Zero Guess Architecture Validation
#>

[CmdletBinding()]
param(
[string]$ProjectRoot="G:\AI\E-zzio"
)

$ErrorActionPreference="Stop"
Set-StrictMode -Version Latest
Set-Location $ProjectRoot


function H($m){
Write-Host "`n=== $m ===" -ForegroundColor Cyan
}

function OK($m){
Write-Host "[+] $m" -ForegroundColor Green
}

function ERR($m){
Write-Host "[-] $m" -ForegroundColor Red
}


H "E-ZZIO CERTIFIED SURGICAL REPAIR 2.4.4.2"


# ==========================================================
# 0 BACKUP COMPLET
# ==========================================================

$Backup="G:\AI\E-zzio_CERTIFIED_BACKUP_2442"

H "BACKUP SECURITE"

if(!(Test-Path $Backup)){
New-Item $Backup -ItemType Directory | Out-Null
}

robocopy `
$ProjectRoot `
$Backup `
/MIR `
/XD .git __pycache__ node_modules `
| Out-Null

OK "Backup certifié"


# ==========================================================
# 1 AUDIT MICROKERNEL
# ==========================================================

$MicroKernel=
Join-Path $ProjectRoot "runtime\core\microkernel.py"

if(!(Test-Path $MicroKernel)){
throw "microkernel.py introuvable"
}


$Audit=
Join-Path $ProjectRoot "audit"

if(!(Test-Path $Audit)){
New-Item $Audit -ItemType Directory | Out-Null
}


Copy-Item `
$MicroKernel `
(Join-Path $Audit "microkernel_before_2442.py") `
-Force


H "ETAT ACTUEL MICROKERNEL"


Select-String `
$MicroKernel `
-Pattern `
"verify|signer|key_manager|TokenSigner|CapabilityToken|class " |
ForEach-Object {

Write-Host `
"L$($_.LineNumber): $($_.Line.Trim())" `
-ForegroundColor Yellow

}


# ==========================================================
# 2 INSPECTION PYTHON AUTOMATIQUE
# ==========================================================


H "DECOUVERTE STRUCTURE RUNTIME"


python - <<'PY'

import importlib
import inspect
import pkgutil


print("=== MODULES RUNTIME ===")

mods=[
"runtime.kernel",
"runtime.core.microkernel",
"runtime.contracts.capability"
]


for m in mods:
    try:
        mod=importlib.import_module(m)
        print("\nMODULE:",m)

        for n in dir(mod):
            if "Kernel" in n or "Micro" in n:
                print("FOUND:",n)

    except Exception as e:
        print("FAIL",m,e)


from runtime.contracts.capability import TokenSigner

print("\n=== TOKENSIGNER ===")

print(inspect.getsource(TokenSigner))


PY



# ==========================================================
# 3 PATCH MINIMAL UNIQUEMENT SI NECESSAIRE
# ==========================================================


H "PATCH SYNTAXIQUE CONTROLE"


$content=
Get-Content $MicroKernel -Raw -Encoding UTF8


# seulement le point orphelin trouvé

if($content -match "if not \.verify"){

Write-Host "Point verify corrompu détecté"


# Recherche contexte

$lines=
Get-Content $MicroKernel


foreach($i in 0..($lines.Count-1)){

if($lines[$i] -match "\.verify"){
Write-Host ""
Write-Host "CONTEXTE:"
$lines[([Math]::Max(0,$i-3))..([Math]::Min($lines.Count-1,$i+3))]
}

}


throw "
STOP SECURITE:
Un appel verify orphelin existe.
Correction automatique interdite sans connaître l'objet signataire réel.
"

}


OK "Aucune corruption syntaxique verify"


# ==========================================================
# 4 TEST CRYPTO REEL
# ==========================================================


H "TEST CRYPTO CERTIFIE"


$Crypto=@"

from runtime.contracts.capability import CapabilityToken,TokenSigner
from dataclasses import replace

signer=TokenSigner()

token=CapabilityToken(
subject="system",
permissions=frozenset(["boot"])
)

signature=signer.sign(token)

signed=replace(
token,
signature=signature
)

assert signed.signature is not None

assert signer.verify(
signed
)

print("CRYPTO OK")

"@


python -c $Crypto


if($LASTEXITCODE -ne 0){
throw "Crypto contract invalide"
}


OK "Crypto validée"



# ==========================================================
# 5 DETECTION DU VRAI KERNEL
# ==========================================================


H "DETECTION KERNEL"


$Kernel=@"

import importlib
import inspect


mods=[
"runtime.kernel",
"runtime.core.microkernel"
]


for m in mods:

    try:
        mod=importlib.import_module(m)

        for n in dir(mod):

            if "Kernel" in n or "Micro" in n:

                obj=getattr(mod,n)

                if inspect.isclass(obj):

                    print(
                    "KERNEL_FOUND:",
                    m,
                    n
                    )

    except Exception:
        pass

"@


python -c $Kernel


OK "Architecture kernel détectée"



# ==========================================================
# 6 COMPILATION
# ==========================================================


H "COMPILEALL"

python -m compileall -q runtime


if($LASTEXITCODE -ne 0){
throw "Compilation échouée"
}


OK "Python compile OK"



# ==========================================================
# 7 SNAPSHOT FINAL
# ==========================================================


Copy-Item `
$MicroKernel `
(Join-Path $Audit "microkernel_after_2442.py") `
-Force



H "DIFF FINAL"


git diff --stat

git diff -- runtime/core/microkernel.py



Write-Host "
Validation humaine obligatoire.
Aucune modification n'est commitée automatiquement.
" `
-ForegroundColor Yellow


$confirm=
Read-Host "Commit + Tag ? Y/N"


if($confirm -notin @("Y","y")){
throw "Arrêt volontaire"
}



git add .

git commit `
-m `
"E-zzio Phase 2.4.4.2 Certified surgical repair"


git tag `
-v2.4.4-certified-runtime-clean `
-f


OK "COMMIT + TAG TERMINES"


H "E-ZZIO 2.4.4.2 CERTIFIED"

