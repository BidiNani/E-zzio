from __future__ import annotations
import json
import sys
from pathlib import Path
from dataclasses import fields
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from core.models.registry import ModelRecord, ModelRegistry

def audit_registry_compatibility() -> Dict[str, Any]:
    registry_path = PROJECT_ROOT / "data" / "models" / "registry.json"
    report = {
        "registry_exists": registry_path.exists(),
        "registry_path": str(registry_path),
        "total_records": 0,
        "valid_records": 0,
        "failed_records": [],
        "dataclass_fields": [f.name for f in fields(ModelRecord)],
        "schema_warnings": []
    }

    if not registry_path.exists():
        report["schema_warnings"].append("Fichier registry.json introuvable. Aucun historique à auditer.")
        return report

    try:
        raw_text = registry_path.read_text(encoding="utf-8")
        data = json.loads(raw_text)
    except Exception as e:
        report["schema_warnings"].append(f"Erreur fatale de lecture JSON du registre : {e}")
        return report

    models_dict = data.get("models", {})
    report["total_records"] = len(models_dict)

    valid_fields = set(report["dataclass_fields"])

    for key, raw in models_dict.items():
        if not isinstance(raw, dict):
            report["failed_records"].append({"key": key, "error": "Entry is not a dictionary"})
            continue

        # Détection de champs inconnus (historiques) ou manquants
        raw_keys = set(raw.keys())
        unknown_keys = list(raw_keys - valid_fields)
        
        # Test d'instanciation sécurisée (filtrage des kwargs non reconnus si nécessaire ou rapport d'alerte)
        filtered_raw = {k: v for k, v in raw.items() if k in valid_fields}
        
        try:
            record = ModelRecord(**filtered_raw)
            report["valid_records"] += 1
            if unknown_keys:
                report["schema_warnings"].append(f"Modèle {key} contient des champs historiques non déclarés dans ModelRecord : {unknown_keys}")
        except Exception as e:
            report["failed_records"].append({"key": key, "error": str(e), "raw": raw})

    return report

def main():
    print("=" * 80)
    print(" GATE 2.2.1 — REGISTRY COMPATIBILITY & HISTORICAL SCHEMA FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    res = audit_registry_compatibility()

    print(f"[-] Fichier registre présent : {res['registry_exists']}")
    print(f"[-] Total enregistrements : {res['total_records']}")
    print(f"[-] Enregistrements valides : {res['valid_records']}")
    print(f"[-] Enregistrements en échec : {len(res['failed_records'])}")

    if res["schema_warnings"]:
        print("\n[!] Avertissements de schéma :")
        for w in res["schema_warnings"]:
            print(f"    - {w}")

    if res["failed_records"]:
        print("\n[X] Enregistrements corrompus ou incompatibles :")
        for f in res["failed_records"]:
            print(f"    - Clé: {f['key']} | Erreur: {f['error']}")

    print("=" * 80)
    print(" BILAN DE L'AUDIT DE COMPATIBILITÉ")
    print("================================================================================")
    if len(res["failed_records"]) == 0:
        print("  - RÉSULTAT : Désérialisation 100% compatible. Aucun risque de purge silencieuse.")
    else:
        print("  - ATTENTION : Des enregistrements provoqueront une exception au load().")
    print("================================================================================")

    out_file = PROJECT_ROOT / "tools" / "registry_compatibility_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print(f"\n[+] Rapport exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()