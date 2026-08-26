#Requires -Version 7.0
<#
.SYNOPSIS
    Micro-diagnostic READ-ONLY de l'identité du RunId du Point Zéro.
.DESCRIPTION
    Prouve au niveau binaire et caractère par caractère la divergence entre
    l'identifiant logique (run_manifest.json) et l'identifiant physique (nom du dossier).
    Aucune modification de fichier.
#>

[CmdletBinding()]
param(
    [string]$PointZeroDir = 'G:\AI\_forensic\ContentTruth\run_20260820_130134_380'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-BytesHex {
    param([string]$Value)
    if ($null -eq $Value) { return '<null>' }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
    return [System.BitConverter]::ToString($bytes)
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — DIAGNOSTIC BINAIRE : RunId VS PointZeroDir" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# 1. Vérification du chemin physique
if (-not (Test-Path -LiteralPath $PointZeroDir -PathType Container)) {
    throw "PointZeroDir introuvable : $PointZeroDir"
}

$manifestPath = Join-Path $PointZeroDir 'run_manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "run_manifest.json introuvable : $manifestPath"
}

# 2. Hachage physique du manifeste
$sha = [System.Security.Cryptography.SHA256]::Create()
$stream = [System.IO.File]::OpenRead($manifestPath)
$manifestSha256 = [System.BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '').ToLowerInvariant()
$stream.Dispose()
$sha.Dispose()

# 3. Extraction de la valeur interne du manifeste
$manifestRaw = [System.IO.File]::ReadAllText($manifestPath, [System.Text.Encoding]::UTF8)
$manifestObj = $manifestRaw | ConvertFrom-Json
$parentRunId = [string]$manifestObj.RunId

# 4. Extraction du segment physique (Expression exacte du moteur)
$leafDir = Split-Path -Leaf $PointZeroDir

# 5. Normalisation candidate
$normalizedDirId = if ($leafDir -like 'run_*') { $leafDir.Substring(4) } else { $leafDir }

# 6. Évaluation des comparaisons
$rawComparisonEqual        = ($parentRunId -eq $leafDir)
$normalizedComparisonEqual = ($parentRunId -eq $normalizedDirId)

# ============================================================================
# RAPPORT DE PREUVE
# ============================================================================

Write-Host "--- [1] CIBLE PHYSIQUE ---" -ForegroundColor Yellow
Write-Host "PointZeroDir          : $PointZeroDir"
Write-Host "ManifestPath          : $manifestPath"
Write-Host "Manifest SHA-256      : $manifestSha256`n"

Write-Host "--- [2] ANALYSE DES VALEURS (RAW) ---" -ForegroundColor Yellow
Write-Host "A. parentRunId (Manifest) :"
Write-Host "   Valeur             : '$parentRunId'"
Write-Host "   Longueur (chars)   : $($parentRunId.Length)"
Write-Host "   Bytes UTF-8 (Hex)  : $(Get-BytesHex $parentRunId)"
Write-Host ""
Write-Host "B. Split-Path -Leaf PointZeroDir :"
Write-Host "   Valeur             : '$leafDir'"
Write-Host "   Longueur (chars)   : $($leafDir.Length)"
Write-Host "   Bytes UTF-8 (Hex)  : $(Get-BytesHex $leafDir)"
Write-Host ""

Write-Host "--- [3] ANALYSE DE LA NORMALISATION ---" -ForegroundColor Yellow
Write-Host "C. Normalized PointZeroDir (sans 'run_') :"
Write-Host "   Valeur             : '$normalizedDirId'"
Write-Host "   Longueur (chars)   : $($normalizedDirId.Length)"
Write-Host "   Bytes UTF-8 (Hex)  : $(Get-BytesHex $normalizedDirId)`n"

Write-Host "--- [4] VERDICT DES COMPARAISONS ---" -ForegroundColor Yellow

if (-not $rawComparisonEqual) {
    Write-Host " [REJET ACTUEL]   (`$parentRunId -eq `$leafDir)               : FALSE" -ForegroundColor Red
    Write-Host "                   -> '$parentRunId' !== '$leafDir'" -ForegroundColor Red
} else {
    Write-Host " [REJET ACTUEL]   (`$parentRunId -eq `$leafDir)               : TRUE (Inattendu)" -ForegroundColor Green
}

if ($normalizedComparisonEqual) {
    Write-Host " [PROPOSITION]    (`$parentRunId -eq `$normalizedDirId)       : TRUE" -ForegroundColor Green
    Write-Host "                   -> Identité logique et identité normalisée concordent à 100%." -ForegroundColor Green
} else {
    Write-Host " [PROPOSITION]    (`$parentRunId -eq `$normalizedDirId)       : FALSE" -ForegroundColor Red
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " DIAGNOSTIC ACHEVÉ — AUCUNE MUTATION EFFECTUÉE" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Cyan