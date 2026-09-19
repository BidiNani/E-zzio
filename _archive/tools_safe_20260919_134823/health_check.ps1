# E-ZZIO V9.2 — Sovereign Platform Health Check & Diagnostics Script
param (
    [string]$BaseUrl = "http://127.0.0.1:8001"
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "     E-ZZIO V9.2 SOVEREIGN PLATFORM HEALTH CHECK           " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$Python = ".\.venv\Scripts\python.exe"

# 1. Verification Frozen Core 3/3
Write-Host "`n[1/4] Verification Frozen Core Cryptographique..." -ForegroundColor Yellow
$HashCapPolicy = "89A770354EBFE4233697F944F0963C3873B811AF1C7DF73E6DACC7AABB389AE2"
$HashRegistry  = "3EE057B327354FAA95CF72A0A920A5EED4FA5DF77AE87298615ED3860FFB0F68"
$HashLedger    = "B26E0D106F0E76121B15B6278F057DEA3ABC1395AA425D86D383E695DFC21C17"

$h1 = (Get-FileHash -Algorithm SHA256 "core/capabilities/capability_policy.py").Hash
$h2 = (Get-FileHash -Algorithm SHA256 "core/capabilities/registry.py").Hash
$h3 = (Get-FileHash -Algorithm SHA256 "core/security/audit_ledger.py").Hash

if ($h1 -eq $HashCapPolicy -and $h2 -eq $HashRegistry -and $h3 -eq $HashLedger) {
    Write-Host "[OK] Frozen Core 3/3 Intact et Immuable." -ForegroundColor Green
} else {
    Write-Error "[FAIL] Frozen Core corrompu !"
    exit 1
}

# 2. Verification Modules V9.2
Write-Host "`n[2/4] Verification des modules natifs V9.2..." -ForegroundColor Yellow
$checkCode = @"
import core.orchestration
import core.agents
import core.artifacts
import core.governance.diff_viewer
print('[OK] Modules V9.2 (orchestration, agents, artifacts, diff_viewer) operationnels.')
"@
& $Python -c $checkCode
if ($LASTEXITCODE -ne 0) {
    Write-Error "[FAIL] Erreur de chargement des modules V9.2"
    exit 1
}

# 3. Sonde Provider Ollama
Write-Host "`n[3/4] Sonde Provider Cognitif..." -ForegroundColor Yellow
$probeCode = @"
import asyncio
from core.cognitive_router import ModelRouter
router = ModelRouter()
health = asyncio.run(router.probe_ollama())
online = health.get('online')
lat = health.get('latency_ms')
cnt = len(health.get('models', []))
print(f'Ollama: Online={online}, Latency={lat}ms, Models={cnt}')
"@
& $Python -c $probeCode

# 4. Audit Ledger Integrity
Write-Host "`n[4/4] Verification de l'Audit Ledger Blockchain..." -ForegroundColor Yellow
$auditCode = @"
from core.security.audit_ledger import audit_ledger
valid, total, err = audit_ledger.verify_chain_integrity()
print(f'Audit Ledger Chain: Valid={valid}, TotalEvents={total}')
assert valid, f'Audit ledger integrity violated: {err}'
"@
& $Python -c $auditCode
if ($LASTEXITCODE -ne 0) {
    Write-Error "[FAIL] Chaine d'audit compromise !"
    exit 1
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "   [PASS] E-ZZIO V9.2 SYSTEM HEALTH: 100% OPERATIONAL      " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan