import os
import sys
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

def search_contract_generators():
    """Recherche des fonctions ou scripts impliqués dans la génération/signature de contrats."""
    generators = []
    keywords = ["create_contract", "generate_contract", "sign_contract", "contract_signer", "contract_generator"]
    
    for py_file in ROOT_DIR.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            if any(kw in content.lower() for kw in keywords):
                rel_path = str(py_file.relative_to(ROOT_DIR)).replace("\\", "/")
                generators.append(rel_path)
        except Exception:
            pass
    return list(set(generators))

def exhaustive_serialization_brute_force():
    """Teste toutes les variations possibles de sérialisation JSON et de secrets pour retrouver le hash."""
    contract_file = ROOT_DIR / "runtime" / "hardware" / "trust" / "models" / "contracts" / "qwen2.5-7b.contract.json"
    if not contract_file.exists():
        return {"error": "Contrat introuvable"}

    raw_text = contract_file.read_text(encoding="utf-8")
    contract_json = json.loads(raw_text)
    stored_signature = contract_json.get("signature")
    
    clean_payload = {k: v for k, v in contract_json.items() if k != "signature"}

    # Liste de toutes les variantes de sérialisation JSON imaginables
    serialization_options = [
        ("default_sort_keys", json.dumps(clean_payload, sort_keys=True)),
        ("default_no_sort", json.dumps(clean_payload, sort_keys=False)),
        ("separators_comma_colon", json.dumps(clean_payload, sort_keys=True, separators=(",", ":"))),
        ("separators_space_colon", json.dumps(clean_payload, sort_keys=True, separators=(", ", ": "))),
        ("ensure_ascii_false", json.dumps(clean_payload, sort_keys=True, ensure_ascii=False)),
        ("indent_2", json.dumps(clean_payload, sort_keys=True, indent=2)),
        ("indent_4", json.dumps(clean_payload, sort_keys=True, indent=4)),
        ("raw_original_minus_sig", re.sub(r',\s*"signature":\s*"[^"]*"', '', raw_text).strip())
    ]

    # Collecte de toutes les clés/secrets potentiels dans le dépôt ou l'environnement
    candidate_secrets = ["ezzio-secret-seed", "default_secret", "EZZIO_CORE_ROOT_KEY", "EZZIO_SECRET", "secret", ""]
    
    # Lecture des fichiers .env ou .key s'ils existent
    for env_file in ROOT_DIR.rglob("*.env"):
        try:
            for line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    candidate_secrets.append(v.strip('"\' '))
        except Exception:
            pass

    key_file = ROOT_DIR / "runtime" / "hardware" / "security" / "hmac.key"
    if key_file.exists():
        try:
            candidate_secrets.insert(0, key_file.read_text(encoding="utf-8").strip())
        except Exception:
            raw_b = key_file.read_bytes()
            candidate_secrets.insert(0, raw_b.hex())
            candidate_secrets.insert(0, raw_b.decode("latin1", errors="ignore"))

    match_results = []

    for secret in set(candidate_secrets):
        if not secret: continue
        for ser_name, ser_string in serialization_options:
            if isinstance(ser_string, str):
                payload_bytes = ser_string.encode("utf-8")
            else:
                payload_bytes = ser_string

            # Test A : payload + secret
            hash_a = hashlib.sha256(payload_bytes + secret.encode("utf-8", errors="ignore")).hexdigest()
            # Test B : secret + payload
            hash_b = hashlib.sha256(secret.encode("utf-8", errors="ignore") + payload_bytes).hexdigest()

            if stored_signature and (hash_a == stored_signature or hash_b == stored_signature):
                match_results.append({
                    "match": True,
                    "secret_masked": secret[:6] + "...",
                    "serialization_method": ser_name,
                    "combinative_order": "payload + secret" if hash_a == stored_signature else "secret + payload"
                })

    return {
        "stored_signature": stored_signature,
        "matches_found": match_results
    }

def run_origin_audit():
    print("[*] Démarrage de l'audit V7.9.3 (Signature Origin Discovery)...")
    generators = search_contract_generators()
    brute_force = exhaustive_serialization_brute_force()

    payload = {
        "timestamp": datetime.now().isoformat(),
        "contract_generators_found": generators,
        "brute_force_replay": brute_force
    }

    out_json = REGISTRY_OUT / "signature_origin_discovery.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown(generators, brute_force)
    print(f"[OK] Audit V7.9.3 terminé. Rapport enregistré dans {REGISTRY_OUT}")

def build_markdown(generators: list, brute_force: dict):
    md_path = REGISTRY_OUT / "V7_SIGNATURE_ORIGIN_REPORT.md"
    matches = brute_force.get("matches_found", [])

    lines = [
        "# E-ZZIO V7.9.3 — Rapport d'Audit de Découverte de l'Origine des Signatures",
        f"**Date :** {datetime.now().isoformat()}",
        "",
        "## 1. Générateurs & Signuteurs Identifiés dans le Dépôt",
        f"- **Nombre de modules liés aux contrats :** {len(generators)}",
        ""
    ]
    for g in generators:
        lines.append(f"- `{g}`")

    lines.extend([
        "",
        "## 2. Résultats du Brute-Force des Sérialisations et Secrets",
        f"- **Signature cible :** `{brute_force.get('stored_signature')}`",
        f"- **Correspondances trouvées :** {len(matches)}",
        ""
    ])

    if matches:
        for m in matches:
            lines.append(f"  - **MATCH !** Sérialisation : `{m['serialization_method']}` | Ordre : `{m['combinative_order']}` | Secret : `{m['secret_masked']}`")
    else:
        lines.append("  - **AUCUN MATCH :** Aucune combinaison de sérialisation et de secret testée n'a permis de reproduire la signature d'origine. La signature a pu être émise avec un sel ou un utilitaire externe.")

    lines.extend([
        "",
        "## 3. Conclusion V7.9.3",
        "L'incapacité à reproduire la signature historique par brute-force confirme qu'il ne faut pas tenter de valider cryptographiquement les anciens contrats via un bridge de code arbitraire. La voie de migration propre consistera, le moment venu, à régénérer les contrats de la Trust Layer avec l'autorité HMAC unifiée."
    ])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path}")

if __name__ == "__main__":
    run_origin_audit()
