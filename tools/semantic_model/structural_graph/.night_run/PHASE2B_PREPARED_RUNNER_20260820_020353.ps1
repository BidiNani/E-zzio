#requires -Version 7.0

[CmdletBinding()]
param(
    [switch]$Run
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Engine = 'G:\AI\E-zzio\Phase2B_v5.2.ps1'
$ExpectedHash = '9473855338424c435659e511f6f4f4712f106b4227965852e92dba12a156b9bb'
$BatchSize = 2000
$ExpectedFileCount = 176064

Write-Host '============================================================' -ForegroundColor Cyan
Write-Host ' E-ZZIO — PHASE 2B PREPARED RUNNER' -ForegroundColor Cyan
Write-Host '============================================================' -ForegroundColor Cyan

Write-Host "[ENGINE] $Engine"

if (-not (Test-Path -LiteralPath $Engine -PathType Leaf)) {
    throw 'ENGINE_NOT_FOUND'
}

$CurrentHash = (Get-FileHash -LiteralPath $Engine -Algorithm SHA256).Hash.ToLowerInvariant()

if ($CurrentHash -ne $ExpectedHash) {
    throw 'FAIL-CLOSED: ENGINE_HASH_CHANGED'
}

Write-Host "[HASH PASS] $CurrentHash" -ForegroundColor Green

if (-not $Run) {
    Write-Host '[SAFE] Aucun lancement demande.' -ForegroundColor Green
    return
}

Write-Host '[AUTHORIZED] Lancement explicite en DryRun.' -ForegroundColor Yellow

& $Engine -DryRun -BatchSize $BatchSize -ExpectedFileCount $ExpectedFileCount

if ($LASTEXITCODE -ne 0) {
    throw "PHASE2B_DRYRUN_FAILED: exit=$LASTEXITCODE"
}

Write-Host '[PASS] DryRun termine.' -ForegroundColor Green
