"""Router /api/models/registry : liste des modeles + etat du KeyPool."""
from fastapi import APIRouter

router = APIRouter(tags=["models"])


@router.get("/api/models/registry")
async def list_models_registry():
    """
    Liste tous les modèles depuis le registre central (data/models/registry.json)
    + état des clés par provider (KeyPoolManager).
    """
    import json
    from pathlib import Path

    from core.models.key_pool import KeyPoolManager

    # 1. Charger le registre
    registry_path = Path("G:/AI/E-zzio/data/models/registry.json")
    registry_models = {}
    if registry_path.exists():
        with open(registry_path, encoding="utf-8") as f:
            data = json.load(f)
            registry_models = data.get("models", {})

    # 2. État du pool
    pool = KeyPoolManager()
    pool_status = {}
    for provider in pool.providers():
        slots = pool.available_slots(provider)
        pool_status[provider] = {
            "available_keys": len(slots),
            "total_keys": len(pool._slots.get(provider, [])),
        }

    # 3. Croiser : grouper par provider
    by_provider = {}
    for model_key, model_data in registry_models.items():
        provider = model_data.get("provider", "unknown")
        model_id = model_data.get("model_id", model_key)
        meta = model_data.get("metadata", {})

        if provider not in by_provider:
            by_provider[provider] = []

        by_provider[provider].append({
            "model_id": model_id,
            "display_name": meta.get("display_name", model_id),
            "context_window": model_data.get("context_window"),
            "max_output_tokens": model_data.get("max_output_tokens"),
            "supports_chat": model_data.get("supports_chat", True),
            "supports_tools": model_data.get("supports_tools", False),
            "supports_reasoning": model_data.get("supports_reasoning", False),
            "lifecycle": model_data.get("lifecycle", "UNKNOWN"),
            "tier": model_data.get("tier", "UNQUALIFIED"),
        })

    # 4. Ajouter Ollama (local)
    ollama_models = []
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                for m in r.json().get("models", []):
                    ollama_models.append({
                        "model_id": m["name"],
                        "display_name": m["name"],
                        "provider": "ollama",
                        "size": m.get("size"),
                    })
    except Exception:
        pass
    by_provider["ollama"] = ollama_models

    return {
        "ok": True,
        "by_provider": by_provider,
        "pool_status": pool_status,
        "total_models": sum(len(v) for v in by_provider.values()),
    }
