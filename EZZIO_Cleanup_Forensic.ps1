#requires -Version 7.4
<#
===============================================================================
 E-ZZIO — CLEANUP FORENSIC ENGINE
 Version : 1.0.0
 Mode    : AUDIT (Default / Read-Only) | QUARANTINE | PURGE
===============================================================================
#>

[CmdletBinding()]
param(
    [ValidateSet('Audit','Quarantine','Purge')]
    [string]$Mode = 'Audit',

    [string]$Root = 'G:\AI\E-zzio',
    [switch]$ConfirmPurge
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RunId = 'run_cleanup_' + (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfffZ')
$PythonExe = Join-Path $Root '.venv\Scripts\python.exe'
$EngineScript = Join-Path $Root 'scripts\cleanup_engine.py'

Write-Host '================================================================================'
Write-Host '                   E-ZZIO — CLEANUP FORENSIC ENGINE'
Write-Host '================================================================================'
Write-Host ('MODE       : ' + $Mode)
Write-Host ('RUN ID     : ' + $RunId)
Write-Host ('ROOT       : ' + $Root)
Write-Host 'SANCTUARY  : 100% IMMUTABLE & PROTECTED'
Write-Host '================================================================================'

if ($Mode -eq 'Purge' -and -not $ConfirmPurge) {
    Write-Host '[FAIL-CLOSED] Le mode PURGE necessite la confirmation explicite -ConfirmPurge.' -ForegroundColor Red
    exit 10
}

if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
    Write-Host ('[FAIL-CLOSED] Python introuvable : {0}' -f $PythonExe) -ForegroundColor Red
    exit 20
}

if (-not (Test-Path -LiteralPath $EngineScript -PathType Leaf)) {
    Write-Host ('[FAIL-CLOSED] Moteur de nettoyage introuvable : {0}' -f $EngineScript) -ForegroundColor Red
    exit 30
}

Write-Host ('Lancement de l''analyse forensique de nettoyage ({0})...' -f $Mode)

& $PythonExe $EngineScript $Mode $RunId
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    $reportDir = Join-Path $Root ('_forensic\cleanup\' + $RunId)
    $reportMd = Join-Path $reportDir 'CLEANUP_FINAL_REPORT.md'
    Write-Host ''
    Write-Host '================================================================================'
    Write-Host '                E-ZZIO CLEANUP FORENSIC — OPERATION COMPLETE'
    Write-Host '================================================================================'
    Write-Host ('Rapports generes sous : ' + $reportDir)
    if (Test-Path -LiteralPath $reportMd -PathType Leaf) {
        Write-Host ''
        Get-Content -LiteralPath $reportMd -Encoding UTF8 | ForEach-Object { Write-Host $_ }
    }
    Write-Host '================================================================================'
}
else {
    Write-Host ('[FAIL-CLOSED] Le moteur de nettoyage a quitte avec l''erreur code : {0}' -f $exitCode) -ForegroundColor Red
    exit $exitCode
}
