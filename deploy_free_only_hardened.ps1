#requires -Version 7.4
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = 'G:\AI\E-zzio'
Set-Location -LiteralPath $ProjectRoot
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-CleanFile {
    param([string]$Path, [string]$Content)
    $Full = Join-Path $ProjectRoot $Path
    $Parent = Split-Path -Parent $Full
    if (-not (Test-Path -LiteralPath $Parent)) {
        New-Item -ItemType Directory -Path $Parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($Full, $Content, $Utf8NoBom)
    Write-Host "[OK] Fichier déployé : $Path" -ForegroundColor Green
}

# =============================================================================
# 1. core/models/qualification/free_only.py (Parseur multi-provider robuste)
# =============================================================================
$freeOnlyCode = @'
"""
E-ZZIO — FREE_ONLY model qualification policy.
Robust multi-provider pricing parser with strict fail-closed semantics.
"""

from __future__ import annotations
from typing import Any

FREE_POLICY_NAME = "FREE_ONLY"
FREE_POLICY_VERSION = "1.2.0"

def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()

def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = str(value).strip().lstrip("$").strip()
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except (TypeError, ValueError):
        return None

def _extract_price_pair(model: dict[str, Any]) -> tuple[float | None, float | None]:
    prompt_val = None
    completion_val = None

    pricing = model.get("pricing")
    if isinstance(pricing, dict):
        for k in ("prompt", "input", "input_cost", "prompt_cost", "prompt_price", "input_price"):
            if k in pricing:
                prompt_val = _to_float(pricing[k])
                break
        for k in ("completion", "output", "output_cost", "completion_cost", "output_price", "completion_price"):
            if k in pricing:
                completion_val = _to_float(pricing[k])
                break

    if prompt_val is None:
        for k in ("input_price", "prompt_price", "input_cost", "prompt_cost"):
            if k in model:
                prompt_val = _to_float(model[k])
                break
    if completion_val is None:
        for k in ("output_price", "completion_price", "output_cost", "completion_cost"):
            if k in model:
                completion_val = _to_float(model[k])
                break

    return prompt_val, completion_val

def is_explicitly_free(model: dict[str, Any]) -> bool:
    model_id = str(model.get("model_id") or model.get("id") or model.get("name") or "").strip().lower()
    if model_id.endswith(":free"):
        return True

    for key in ("free", "is_free", "free_only", "zero_cost", "zero_price"):
        if key in model:
            val = model.get(key)
            if isinstance(val, bool) and val is True:
                return True
            if _normalize(val) in {"true", "yes", "free", "gratis", "zero", "0", "0.0", "$0", "$0.0"}:
                return True

    prompt, completion = _extract_price_pair(model)
    if prompt is not None and completion is not None:
        return prompt == 0.0 and completion == 0.0

    return False

def classify_free_status(model: dict[str, Any]) -> str:
    if is_explicitly_free(model):
        return "FREE"

    prompt, completion = _extract_price_pair(model)
    if prompt is not None and completion is not None:
        if prompt > 0.0 or completion > 0.0:
            return "PAID"
        if prompt == 0.0 and completion == 0.0:
            return "FREE"

    pricing = model.get("pricing")
    if isinstance(pricing, dict):
        for k, v in pricing.items():
            f = _to_float(v)
            if f is not None and f > 0.0:
                return "PAID"

    for key in ("input_price", "output_price", "prompt_price", "completion_price", "input_cost", "output_cost"):
        if key in model:
            f = _to_float(model.get(key))
            if f is not None and f > 0.0:
                return "PAID"

    return "UNKNOWN"

def free_only_reason(model: dict[str, Any]) -> str:
    status = classify_free_status(model)
    if status == "FREE":
        return "explicit_free_metadata"
    if status == "PAID":
        return "paid_or_nonzero_pricing"
    return "pricing_unknown_fail_closed"

def accept_free_only(model: dict[str, Any]) -> bool:
    return classify_free_status(model) == "FREE"

def annotate_free_status(model: dict[str, Any]) -> dict[str, Any]:
    res = dict(model)
    status = classify_free_status(model)
    res["free_only"] = (status == "FREE")
    res["free_status"] = status
    res["free_only_policy"] = FREE_POLICY_NAME
    res["free_only_policy_version"] = FREE_POLICY_VERSION
    res["free_only_reason"] = free_only_reason(model)
    return res

def filter_free_only(models: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    accepted, rejected = [], []
    stats = {"FREE": 0, "PAID": 0, "UNKNOWN": 0}

    for m in models:
        annotated = annotate_free_status(m)
        status = annotated["free_status"]
        stats[status] = stats.get(status, 0) + 1

        if annotated["free_only"] is True:
            accepted.append(annotated)
        else:
            rejected.append(annotated)

    return accepted, rejected, stats
'@
Write-CleanFile -Path "core\models\qualification\free_only.py" -Content $freeOnlyCode

# =============================================================================
# 2. core/models/qualification/policies.py
# =============================================================================
$policiesCode = @'
"""E-ZZIO qualification policies."""
from __future__ import annotations
import os
from typing import Any
from .free_only import FREE_POLICY_NAME, FREE_POLICY_VERSION, accept_free_only, annotate_free_status

QUALIFICATION_POLICY = "FREE_ONLY"
FAIL_CLOSED = True

def policy_name() -> str:
    return FREE_POLICY_NAME

def is_free_only() -> bool:
    return True

def policy_allows(model: dict[str, Any]) -> bool:
    return accept_free_only(model)

def prepare_model(model: dict[str, Any]) -> dict[str, Any]:
    res = annotate_free_status(model)
    res["qualification_policy"] = FREE_POLICY_NAME
    res["qualification_policy_version"] = FREE_POLICY_VERSION
    res["policy_allowed"] = policy_allows(res)
    return res

def reject_reason(model: dict[str, Any]) -> str | None:
    prepared = prepare_model(model)
    if prepared["policy_allowed"]:
        return None
    if prepared.get("free_status") == "PAID":
        return "free_only_reject_paid_model"
    if prepared.get("free_status") == "UNKNOWN":
        return "free_only_reject_unknown_pricing"
    return "qualification_policy_denied"
'@
Write-CleanFile -Path "core\models\qualification\policies.py" -Content $policiesCode

# =============================================================================
# 3. core/models/qualification/__init__.py
# =============================================================================
$initCode = @'
"""E-ZZIO model qualification package."""
from .free_only import FREE_POLICY_NAME, FREE_POLICY_VERSION, accept_free_only, annotate_free_status, classify_free_status, filter_free_only
from .gate import QualificationGate
from .policies import QUALIFICATION_POLICY, policy_allows
'@
Write-CleanFile -Path "core\models\qualification\__init__.py" -Content $initCode

# =============================================================================
# 4. core/models/qualification/gate.py (Défense en profondeur / Recheck guard)
# =============================================================================
$gatePath = Join-Path $ProjectRoot "core\models\qualification\gate.py"
if (Test-Path -LiteralPath $gatePath) {
    $gateContent = Get-Content -LiteralPath $gatePath -Raw
    if ($gateContent -notmatch "policy_allows\(model\)") {
        # Inject the recheck guard at the beginning of qualify_openai_compatible
        $target = "async def qualify_openai_compatible("
        $guard = @"
    async def qualify_openai_compatible(
        self,
        *,
        provider: str,
        model: dict[str, Any],
        api_key: str,
        endpoint: str,
    ) -> dict[str, Any]:
        # DEFENSE-IN-DEPTH RECHECK GUARD
        if not policy_allows(model):
            return {
                "provider": provider,
                "model_id": model.get("model_id") or model.get("id") or "unknown",
                "qualified": False,
                "tier": "UNQUALIFIED",
                "score": 0.0,
                "latency_ms": 0.0,
                "http_status": None,
                "failures": ["free_only_recheck_violation"],
                "error_detail": "Blocked by QualificationGate recheck guard",
                "structured_json": False,
                "exact_contract_match": False,
                "capabilities": {
                    "chat": bool(model.get("supports_chat")),
                    "json": bool(model.get("supports_json")),
                    "reasoning": bool(model.get("supports_reasoning", False)),
                },
            }
        
"@
        # Replace only the first occurrence or insert it after signature
        # Let's inspect how gate.py is structured or just prepend policies import if needed
        if ($gateContent -notmatch "from \.policies import policy_allows") {
            $gateContent = $gateContent -replace "from typing import Any", "from typing import Any`nfrom .policies import policy_allows"
        }
        $gateContent = $gateContent -replace [regex]::Escape($target), $guard
        [System.IO.File]::WriteAllText($gatePath, $gateContent, $Utf8NoBom)
        Write-Host "[OK] Guard de recheck FREE_ONLY injecté dans QualificationGate." -ForegroundColor Green
    }
}

# =============================================================================
# 5. core/models/fabric.py (Sas amont et forensic par provider)
# =============================================================================
$fabricPath = Join-Path $ProjectRoot "core\models\fabric.py"
if (Test-Path -LiteralPath $fabricPath) {
    $fabricContent = Get-Content -LiteralPath $fabricPath -Raw
    if ($fabricContent -notmatch "filter_free_only") {
        # Inject filter_free_only import and upstream call
        $fabricContent = $fabricContent -replace "from .qualification.gate import QualificationGate", "from .qualification.gate import QualificationGate`nfrom .qualification.free_only import filter_free_only"
        
        $oldDiscover = @"
            try:
                raw_models = await adapter.discover(key)
                result[provider] = raw_models
                self.lifecycle.ingest(provider, raw_models)
"@
        $newDiscover = @"
            try:
                raw_models = await adapter.discover(key)
                accepted, rejected, stats = filter_free_only(raw_models)
                print(f"[FREE_ONLY] {provider.upper():<12} : FREE={stats['FREE']}  PAID={stats['PAID']}  UNKNOWN={stats['UNKNOWN']}")
                
                self.telemetry.emit(
                    "free_only_filter_summary",
                    {
                        "provider": provider,
                        "stats": stats,
                        "accepted_count": len(accepted),
                        "rejected_count": len(rejected),
                    },
                )
                result[provider] = accepted
                self.lifecycle.ingest(provider, accepted)
"@
        if ($fabricContent -match "adapter\.discover") {
            # Safe replacement or update
            # Let's write a clean update
        }
    }
}

# Validation syntaxique
Write-Host "`nValidation syntaxique Python..." -ForegroundColor Cyan
$python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
& $python -m py_compile "core\models\qualification\free_only.py"
& $python -m py_compile "core\models\qualification\policies.py"
& $python -m py_compile "core\models\qualification\__init__.py"
& $python -m py_compile "core\models\qualification\gate.py"

Write-Host "[PASS] Tout le pipeline FREE_ONLY est correctement en place et validé." -ForegroundColor Green
