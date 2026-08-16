import os
import sys
import json
import ast
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path("G:/AI/E-zzio").resolve()
REGISTRY_OUT = ROOT_DIR / "runtime" / "audit" / "intelligence_scan" / "V7_REGISTRY"
REGISTRY_OUT.mkdir(parents=True, exist_ok=True)

TARGETS = [
    "runtime/hardware/trust/models/contract_signer.py",
    "runtime/hardware/trust/models/registry.py",
    "runtime/hardware/trust/execution/attestation/verifier.py",
    "runtime/contracts/capability.py"
]

def analyze_crypto_primitives(file_path: Path) -> dict:
    if not file_path.exists():
        return {"exists": False}
    content = file_path.read_text(encoding="utf-8", errors="replace")
    
    has_hmac = "hmac.new" in content or "hmac" in content.lower()
    has_sha = "hashlib.sha256" in content
    has_concat = "+" in content and any(k in content.lower() for k in ["secret", "seed", "key"])
    
    key_source = []
    if "env" in content.lower() or "os.environ" in content:
        key_source.append("ENV")
    if "key" in content.lower() or "path" in content.lower() or "read_text" in content:
        key_source.append("FILE / PATH")

    snippets = []
    for line in content.splitlines():
        if any(k in line.lower() for k in ["def sign", "def verify", "hmac", "sha256", "secret", "digest"]):
            snippets.append(line.strip())

    return {
        "exists": True,
        "path": str(file_path.relative_to(ROOT_DIR)).replace("\\", "/"),
        "has_hmac": has_hmac,
        "has_sha256": has_sha,
        "has_concat_hashing": has_concat,
        "key_sources_detected": key_source,
        "relevant_snippets": snippets[:10]
    }

def run_normalization_audit():
    print("[*] Démarrage de l'audit de normalisation de signature V7.8...")
    results = {}

    for rel_path in TARGETS:
        full_path = ROOT_DIR / rel_path
        results[rel_path] = analyze_crypto_primitives(full_path)

    payload = {
        "timestamp": datetime.now().isoformat(),
        "normalization_audit": results
    }

    out_json = REGISTRY_OUT / "signature_normalization_audit.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    build_markdown(results)
    print(f"[OK] Audit V7.8 terminé. Rapport généré dans {REGISTRY_OUT}")

def build_markdown(results: dict):
    md_path = REGISTRY_OUT / "V7_SIGNATURE_AUTHORITY_MATRIX.md"
    lines = [
        "# E-ZZIO V7.8 — Matrice de l'Autorité de Signature & Normalisation",
        f"**Date :** {datetime.now().isoformat()}",
        "",
        "## Analyse Comparative des Primitives Cryptographiques",
        ""
    ]

    for path, data in results.items():
        lines.append(f"### Module : `{path}`")
        if not data.get("exists"):
            lines.append("- **Statut :** `INTROUVABLE`")
            lines.append("")
            continue
            
        lines.extend([
            f"- **Utilise HMAC (`hmac.new`) :** `{data.get('has_hmac')}`",
            f"- **Utilise SHA256 (`hashlib.sha256`) :** `{data.get('has_sha256')}`",
            f"- **Indices de hachage par concaténation (Secret + Payload) :** `{data.get('has_concat_hashing')}`",
            f"- **Sources de clés identifiées :** `{data.get('key_sources_detected')}`",
            f"- **Extraits de code pertinents :**",
        ])
        for snip in data.get('relevant_snippets', []):
            lines.append(f"  - `{snip}`")
        lines.append("")

    lines.extend([
        "",
        "## Recommandation de Normalisation (V7.8)",
        "Pour garantir une interopérabilité parfaite entre l'émetteur (`contract_signer.py`) et le vérificateur (`models/registry.py`), la primitive cryptographique doit être unifiée sous un standard unique : **HMAC-SHA256** standardisé, éliminant toute construction par concaténation brute."
    ])

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Rapport Markdown généré : {md_path}")

if __name__ == "__main__":
    run_normalization_audit()
