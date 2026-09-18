# ============================================================================
# E-ZZIO — Wrapper regen_manifest.py
# Force le bon interpréteur (venv) et le bon cwd (racine backend)
# Usage : .\regen-manifest.ps1   (ou chemin absolu, marche partout)
# ============================================================================
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py   = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Error "Venv introuvable : $py"
    exit 1
}

$script = Join-Path $root "runtime\regen_manifest.py"
if (-not (Test-Path $script)) {
    Write-Error "Script introuvable : $script"
    exit 1
}

Set-Location $root
& $py $script @args
exit $LASTEXITCODE