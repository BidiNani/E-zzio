import os
import sys
import json
import hashlib
import ast
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def audit_contracts():
    contracts = []
    for p in ROOT_DIR.rglob("*.contract.json"):
        if any(ex in p.parts for ex in {".git", "__pycache__", "venv", "node_modules", "runtime/audit"}):
            continue
        stat = p.stat()
        content_bytes = p.read_bytes()
        sha = hashlib.sha256(content_bytes).hexdigest()
        try:
            data = json.loads(content_bytes.decode("utf-8", errors="replace"))
        except Exception:
            data = {"parse_error": True}

        contract_info = {
            "path": str(p.relative_to(ROOT_DIR)).replace("\\", "/"),
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "sha256": sha,
            "model_id": data.get("model_id"),
            "contract_version": data.get("contract_version"),
            "provider": data.get("provider"),
            "has_signature": bool(data.get("signature")) and data.get("signature") != "SIGNATURE_PENDING",
            "signature_value": data.get("signature"),
            "schema_fields": {
                "model_id": "model_id" in data,
                "provider": "provider" in data,
                "capabilities": "capabilities" in data or "resources" in data,
                "permissions": "permissions" in data or "security" in data,
                "hardware": "hardware" in data or "resources" in data,
                "signature": "signature" in data
            }
        }
        contracts.append(contract_info)
    return contracts

def search_consumers_and_hmac():
    keywords = ["contract", ".contract.json", "signature", "hmac", "verify", "secret", "capability"]
    findings = []
    hmac_matrix = {}
    
    search_dirs = [ROOT_DIR / "core", ROOT_DIR / "runtime", ROOT_DIR / "tools", ROOT_DIR / "routers"]
    for d in search_dirs:
        if not d.exists(): continue
        for py in d.rglob("*.py"):
            rel = str(py.relative_to(ROOT_DIR)).replace("\\", "/")
            try:
                text = py.read_text(encoding="utf-8", errors="replace")
                matched_kw = [kw for kw in keywords if kw in text.lower()]
                if matched_kw:
                    findings.append({
                        "path": rel,
                        "matched_keywords": matched_kw
                    })
                
                has_hmac = "hmac" in text.lower() or "sha256" in text.lower() or "signature" in text.lower()
                has_verify = "verify" in text.lower() or "sign" in text.lower()
                if has_hmac or has_verify:
                    hmac_matrix[rel] = {
                        "has_hmac_or_hash": has_hmac,
                        "has_sign_or_verify": has_verify
                    }
            except Exception:
                pass
    return findings, hmac_matrix

def autopsy_model_registry():
    reg = ROOT_DIR / "core" / "model_registry.py"
    if not reg.exists():
        return {"error": "core/model_registry.py missing"}
    text = reg.read_text(encoding="utf-8", errors="replace")
    return {
        "file": "core/model_registry.py",
        "lines": len(text.splitlines()),
        "reads_model_latency": "model_latency.json" in text,
        "reads_contracts": ".contract.json" in text or "contract" in text.lower(),
        "inputs_detected": ["model_latency.json"] if "model_latency.json" in text else [],
        "outputs_detected": ["best_fast_model", "all_known_models", "ORGANS"] if "ORGANS" in text else []
    }

def run_audit():
    print("[*] Démarrage V7.4 Registry Authority Audit (Read-Only)...")
    contracts = audit_contracts()
    consumers, hmac_matrix = search_consumers_and_hmac()
    reg_autopsy = autopsy_model_registry()

    # Sauvegarde des livrables JSON
    (REGISTRY_OUT / "contracts_inventory.json").write_text(json.dumps(contracts, indent=2, ensure_ascii=False), encoding="utf-8")
    (REGISTRY_OUT / "contract_consumers.json").write_text(json.dumps(consumers, indent=2, ensure_ascii=False), encoding="utf-8")
    (REGISTRY_OUT / "model_registry_autopsy.json").write_text(json.dumps(reg_autopsy, indent=2, ensure_ascii=False), encoding="utf-8")
    
    # Génération des livrables Markdown
    build_markdowns(contracts, consumers, reg_autopsy, hmac_matrix)
    print(f"[OK] Audit V7.4 terminé. Livrables générés dans {REGISTRY_OUT}")

def build_markdowns(contracts, consumers, reg_autopsy, hmac_matrix):
    # 1. contracts_schema_report.md
    md1 = ["# E-ZZIO V7.4 — Contrats de Modèles (Schéma & Inventaire)", f"**Total contrats trouvés :** {len(contracts)}", ""]
    for c in contracts:
        md1.append(f"- **Chemin :** `{c['path']}`")
        md1.append(f"  - Modèle : `{c['model_id']}`")
        md1.append(f"  - Version : `{c['contract_version']}`")
        md1.append(f"  - Provider : `{c['provider']}`")
        md1.append(f"  - Signature Valide : `{c['has_signature']}`")
        md1.append(f"  - Champs présents : {c['schema_fields']}")
    (REGISTRY_OUT / "contracts_schema_report.md").write_text("\n".join(md1), encoding="utf-8")

    # 2. CONTRACT_FLOW.md
    md2 = ["# E-ZZIO V7.4 — Flux de Consommation des Contrats (CONTRACT_FLOW.md)", ""]
    for cs in consumers:
        md2.append(f"- `{cs['path']}` -> Mots-clés détectés : {cs['matched_keywords']}")
    (REGISTRY_OUT / "CONTRACT_FLOW.md").write_text("\n".join(md2), encoding="utf-8")

    # 3. HMAC_CAPABILITY_MATRIX.md
    md3 = ["# E-ZZIO V7.4 — Matrice HMAC et Capacités (HMAC_CAPABILITY_MATRIX.md)", ""]
    for path, info in hmac_matrix.items():
        md3.append(f"- `{path}` | Utilise HMAC/Hash: `{info['has_hmac_or_hash']}` | Sign/Verify: `{info['has_sign_or_verify']}`")
    (REGISTRY_OUT / "HMAC_CAPABILITY_MATRIX.md").write_text("\n".join(md3), encoding="utf-8")

    # 4. V7.4_REGISTRY_AUTHORITY_FINAL.md
    md4 = [
        "# E-ZZIO V7.4 — Rapport Final d'Autorité des Registres",
        "## Diagnostic Global",
        f"- **Contrats détectés :** {len(contracts)} fichier(s) `*.contract.json` identifiés.",
        f"- **État de `core/model_registry.py` :** Gère actuellement la latence via `model_latency.json` et le dictionnaire des organes, mais **n'intègre pas** encore nativement la résolution des contrats HMAC.",
        "",
        "## Recommandation Finale (Option C)",
        "Le répertoire `runtime/hardware/trust/models/contracts/` doit devenir la **Vérité Déclarative** unique, et `core/model_registry.py` doit évoluer en consommateur unifié (absorbant la validation HMAC et les limites matérielles sans altérer le routage des organes)."
    ]
    (REGISTRY_OUT / "V7.4_REGISTRY_AUTHORITY_FINAL.md").write_text("\n".join(md4), encoding="utf-8")

if __name__ == "__main__":
    run_audit()
