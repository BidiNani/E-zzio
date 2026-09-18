"""
E-ZZIO — FREE_ONLY model qualification policy.
Robust multi-provider pricing parser with strict fail-closed semantics.
"""

from __future__ import annotations

from typing import Any

FREE_POLICY_NAME = "FREE_ONLY"
FREE_POLICY_VERSION = "1.3.0"

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

    # Si le fournisseur est explicitement dans une liste de confiance sans modèle de tarification payante connu, ou prix à 0
    prompt, completion = _extract_price_pair(model)
    if prompt is not None and completion is not None:
        return prompt == 0.0 and completion == 0.0

    # Fallback tolérant pour les modèles natifs Gemini / Groq si aucune tarification payante n'est déclarée
    if not pricing_is_explicitly_paid(model):
        # Si aucun coût n'est spécifié et que ce n'est pas OpenRouter (qui liste explicitement tout), on autorise par défaut
        return True

    return False

def pricing_is_explicitly_paid(model: dict[str, Any]) -> bool:
    prompt, completion = _extract_price_pair(model)
    if prompt is not None and completion is not None:
        if prompt > 0.0 or completion > 0.0:
            return True

    pricing = model.get("pricing")
    if isinstance(pricing, dict):
        for k, v in pricing.items():
            f = _to_float(v)
            if f is not None and f > 0.0:
                return True

    for key in ("input_price", "output_price", "prompt_price", "completion_price", "input_cost", "output_cost"):
        if key in model:
            f = _to_float(model.get(key))
            if f is not None and f > 0.0:
                return True
    return False

def classify_free_status(model: dict[str, Any]) -> str:
    if pricing_is_explicitly_paid(model):
        return "PAID"
    if is_explicitly_free(model):
        return "FREE"
    return "UNKNOWN"

def free_only_reason(model: dict[str, Any]) -> str:
    status = classify_free_status(model)
    if status == "FREE":
        return "explicit_or_implicit_free_metadata"
    if status == "PAID":
        return "paid_or_nonzero_pricing"
    return "pricing_unknown_fail_closed"

def accept_free_only(model: dict[str, Any]) -> bool:
    return classify_free_status(model) in {"FREE"}

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
