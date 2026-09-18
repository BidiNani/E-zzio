"""
core/api/state_store.py — Persistance JSON légère pour l'API E-zzio.

Fournit une API simple : load(name), save(name, data), append(name, item).
Chaque "state" est un fichier JSON dans runtime/state/{name}.json.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

_STATE_DIR = Path(__file__).resolve().parents[2] / "runtime" / "state"
_STATE_DIR.mkdir(parents=True, exist_ok=True)


def _path(name: str) -> Path:
    return _STATE_DIR / f"{name}.json"


def load(name: str, default: Any = None) -> Any:
    """Charge un état JSON ou retourne la valeur par défaut."""
    p = _path(name)
    if not p.exists():
        return default if default is not None else []
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []


def save(name: str, data: Any) -> None:
    """Écrit un état JSON."""
    p = _path(name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append(name: str, item: dict[str, Any]) -> dict[str, Any]:
    """Ajoute un élément avec ID + timestamp automatiques."""
    items = load(name, [])
    item.setdefault("id", str(uuid.uuid4()))
    item.setdefault("created_at", datetime.utcnow().isoformat() + "Z")
    items.append(item)
    save(name, items)
    return item


def update(name: str, item_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    """Met à jour un élément par ID."""
    items = load(name, [])
    for item in items:
        if item.get("id") == item_id:
            item.update(patch)
            item["updated_at"] = datetime.utcnow().isoformat() + "Z"
            save(name, items)
            return item
    return None


def delete(name: str, item_id: str) -> bool:
    """Supprime un élément par ID."""
    items = load(name, [])
    new = [i for i in items if i.get("id") != item_id]
    if len(new) == len(items):
        return False
    save(name, new)
    return True
