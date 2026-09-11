#Requires -Version 7.0
<#
.SYNOPSIS
    Audit statique READ-ONLY de la résolution de manifeste dans EZZIO_Build_SemanticState.
.DESCRIPTION
    Analyse l'AST et les lignes de code sans aucune exécution ni modification de fichier.
    Cible : Résolution de chemins, recherche de manifests, extraction du RunId.
#>

[CmdletBinding()]
param(
    [string]$TargetScript = "G:\AI\E-zzio\EZZIO_Build_SemanticState_v0.1.1.ps1"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " E-ZZIO — AUDIT STATIQUE : RÉSOLUTION DU MANIFESTE" -ForegroundColor Cyan
Write-Host " CIBLE : $TargetScript" -ForegroundColor Yellow
Write-Host "============================================================`n" -ForegroundColor Cyan

if (-not (Test-Path -LiteralPath $TargetScript -PathType Leaf)) {
    throw "Script cible introuvable : $TargetScript"
}

# 1. Parsing AST
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($TargetScript, [ref]$tokens, [ref]$errors)

if ($errors.Count -gt 0) {
    Write-Host "[WARN] Erreurs de syntaxe détectées dans le script cible :" -ForegroundColor Red
    foreach ($err in $errors) {
        Write-Host "  Ligne $($err.Extent.StartLineNumber) : $($err.Message)" -ForegroundColor Red
    }
}

# 2. Recherche ciblée des patterns à risque dans l'AST
Write-Host "[1] ANALYSE DES APPELS DE COMMANDES (Recherche / Résolution)" -ForegroundColor Yellow

$commandElements = $ast.FindAll({
    param($node)
    $node -is [System.Management.Automation.Language.CommandAst] -and
    ($node.GetCommandName() -match '^(Get-ChildItem|Resolve-Path|Join-Path|Get-Item|Test-Path)$')
}, $true)

foreach ($cmd in $commandElements) {
    $lineText = $cmd.Extent.Text
    $lineNum  = $cmd.Extent.StartLineNumber
    if ($lineText -match 'manifest|PointZero|RunId|Topology|records') {
        Write-Host "  Ligne $($lineNum.ToString().PadLeft(4)) | $lineText" -ForegroundColor DarkCyan
    }
}

# 3. Extraction textuelle contextuelle des assignations clés
Write-Host "`n[2] LIGNES CLÉS LIÉES AUX MANIFESTES ET RUN_ID" -ForegroundColor Yellow

$lines = [System.IO.File]::ReadAllLines($TargetScript)
$keywords = 'manifest|parent_point_zero|parentrun|pointzerodir|runid'

for ($i = 0; $i -lt $lines.Count; $i++) {
    $lineNum = $i + 1
    $currentLine = $lines[$i]

    if ($currentLine -match $keywords -and $currentLine -notmatch '^\s*#') {
        # Affichage avec contexte de 1 ligne avant/après si pertinent
        Write-Host "------------------------------------------------------------" -ForegroundColor DarkGray
        Write-Host "Ligne $lineNum :" -ForegroundColor Yellow
        
        $start = [Math]::Max(0, $i - 1)
        $end   = [Math]::Min($lines.Count - 1, $i + 1)
        
        for ($j = $start; $j -le $end; $j++) {
            $prefix = if ($j -eq $i) { ">>> " } else { "    " }
            $color  = if ($j -eq $i) { "White" } else { "DarkGray" }
            Write-Host "$prefix$($j + 1) | $($lines[$j])" -ForegroundColor $color
        }
    }
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " AUDIT TERMINÉ — AUCUNE MUTATION EFFECTUÉE" -ForegroundColor Green
Write-Host "============================================================`n" -ForegroundColor Cyan