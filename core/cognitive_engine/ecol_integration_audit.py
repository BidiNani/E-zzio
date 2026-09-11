"""
E-ZZIO V7.60.0 — ECOL Integration Audit
Scanne les répertoires core et runtime pour identifier les points d'appel
directs aux LLM, aux anciens routeurs et aux registres de décisions existants.
"""

import json
import re
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(r"G:\AI\E-zzio")
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "ecol_integration_audit_report.json"

SEARCH_PATTERNS = [
    r"ollama",
    r"openai",
    r"anthropic",
    r"client\.chat",
    r"requests\.post",
    r"router_decisions",
    r"experience_ledger",
    r"model_registry",
]


def audit_integration():
    print("[*] Lancement de l'audit d'intégration ECOL...")
    findings = []

    for target_dir in ["core", "runtime"]:
        dir_path = ROOT_DIR / target_dir
        if not dir_path.exists():
            continue

        for path in dir_path.rglob("*.py"):
            rel_path = path.relative_to(ROOT_DIR).as_posix()
            if ".venv" in rel_path or "__pycache__" in rel_path:
                continue

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                matched_patterns = []
                for pattern in SEARCH_PATTERNS:
                    if re.search(pattern, content, re.IGNORECASE):
                        matched_patterns.append(pattern)

                if matched_patterns:
                    findings.append({"file": rel_path, "matched_triggers": matched_patterns, "size_bytes": path.stat().st_size})
            except Exception:
                continue

    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "total_files_flagged": len(findings), "integration_targets": findings}

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print(" ECOL INTEGRATION AUDIT REPORT (V7.60.0)")
    print("=" * 65)
    print(f" Fichiers identifiés avec des déclencheurs LLM/Registres : {len(findings)}")
    print("-" * 65)
    for item in findings[:15]:
        triggers = ", ".join(item["matched_triggers"])
        print(f"  - {item['file']} (Triggers: {triggers})")
    if len(findings) > 15:
        print(f"  ... et {len(findings) - 15} autres fichiers dans le rapport complet.")
    print("=" * 65)
    print(f" Rapport exporté : {OUTPUT_REPORT}")


if __name__ == "__main__":
    audit_integration()
