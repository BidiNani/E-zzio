#!/usr/bin/env python
"""
Génère data/models/registry.json depuis registry.py.

SOURCE UNIQUE :
  - core/routing/registry.py  (modèles cloud + local)
  - core/routing/model_registry.py (rôles métier)

USAGE :
    python scripts/build_registry.py            # génère + écrit
    python scripts/build_registry.py --check    # exit 1 si différent
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.routing.model_registry import (  # noqa: E402
    canonical_model_registry,
)
from core.routing.registry import (  # noqa: E402
    PROVIDERS,
)
from core.routing.registry import (
    all_local as all_local_models,
)
from core.routing.registry import (
    all_models as all_cloud_models,
)

OUTPUT_PATH = ROOT / "data" / "models" / "registry.json"


def build_registry_data() -> dict:
    """Construit la structure JSON du registre."""
    data = {
        "version": 1,
        "generated_from": "core/routing/registry.py + model_registry.py",
        "providers": {},
        "models": {},
        "counts": {},
    }

    # 1. Providers cloud (structure)
    for provider_name, provider in PROVIDERS.items():
        data["providers"][provider_name] = {
            "base_url": provider.base_url,
            "default_model": provider.default_model,
            "fallback_models": list(provider.fallback_models),
            "api_key_env": list(provider.api_key_env),
            "models_count": len([m for m in provider.models if not m.deprecated_at]),
        }

    # 2. Modèles avec rôles (source de vérité pour l'app)
    for record in canonical_model_registry.list_models(
        qualified_only=False,
        include_disabled=True,
    ):
        data["models"][record.name] = {
            "name": record.name,
            "source": record.source.name,
            "role": record.role,
            "roles": list(record.roles),
            "thinking_level": record.thinking_level,
            "enabled": record.enabled,
        }

    # 3. Counts
    cloud = all_cloud_models()
    local = all_local_models()
    data["counts"] = {
        "cloud_active": len(cloud),
        "local_active": len(local),
        "with_roles": len(data["models"]),
        "providers": len(PROVIDERS),
    }

    return data


def main() -> int:
    check_only = "--check" in sys.argv
    data = build_registry_data()
    new_content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    if check_only:
        if not OUTPUT_PATH.exists():
            print(f"[ECHEC] {OUTPUT_PATH.relative_to(ROOT)} n'existe pas")
            return 1
        current = OUTPUT_PATH.read_text(encoding="utf-8")
        if current != new_content:
            print(f"[ECHEC] {OUTPUT_PATH.relative_to(ROOT)} est obsolète")
            print("        Lancer : python scripts/build_registry.py")
            return 1
        print(f"[OK] {OUTPUT_PATH.relative_to(ROOT)} est à jour")
        return 0

    # Écriture
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(new_content, encoding="utf-8")
    print(f"[OK] {OUTPUT_PATH.relative_to(ROOT)} généré ({len(new_content)} octets)")
    print(f"     Providers : {data['counts']['providers']}")
    print(f"     Cloud actifs : {data['counts']['cloud_active']}")
    print(f"     Local actifs : {data['counts']['local_active']}")
    print(f"     Modèles avec rôles : {data['counts']['with_roles']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
