from __future__ import annotations
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
EXCLUDED_DIRS = {"audit", "tests", "snapshot", "snapshots", "backup", "backups", "old", "archive", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", "tools"}

def inspect_snippets(file_rel_path: str, keywords: set[str], context_lines: int = 3) -> None:
    p = PROJECT_ROOT / file_rel_path
    if not p.exists():
        print(f"❌ Fichier introuvable : {file_rel_path}")
        return
    
    print(f"\n📁 FICHIER : {file_rel_path}")
    print("-" * 80)
    try:
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        for idx, line in enumerate(lines, 1):
            if any(kw in line.lower() for kw in keywords):
                start = max(0, idx - 1 - context_lines)
                end = min(len(lines), idx + context_lines)
                print(f"--- Contexte autour de la ligne {idx} ---")
                for sub_i in range(start, end):
                    marker = ">>" if sub_i == idx - 1 else "  "
                    print(f"{marker} {sub_i+1:04d} | {lines[sub_i]}")
    except Exception as e:
        print(f"  ❌ Erreur lecture : {e}")

def search_physical_tags(tag: str) -> list[str]:
    matches = []
    for p in PROJECT_ROOT.glob("**/*"):
        if set(p.parts) & EXCLUDED_DIRS or p.is_dir():
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            if tag in content.lower():
                matches.append(str(p.relative_to(PROJECT_ROOT)))
        except Exception:
            continue
    return matches

def main():
    print("=" * 80)
    print(" GATE v6.45.55 — ULTIMATE PROVENANCE & WIRING FORENSICS")
    print("=" * 80)
    print(f"[RACINE] {PROJECT_ROOT}\n")

    print("[1] UTILISATION D'AgentProviderAdapter DANS CognitiveGateway :")
    inspect_snippets("core/cognition/cognitive_gateway.py", {"agentprovideradapter", "provider", "model", "gemini"})

    print("\n[2] UTILISATION D'AgentProviderAdapter DANS coding_agent_loop :")
    inspect_snippets("core/agent/coding_agent_loop.py", {"agentprovideradapter", "provider", "model", "backend"})

    print("\n[3] RECHERCHE PHYSIQUE DE L'ORIGINE DES TAGS OLLAMA :")
    for tag in ["ezzio-granite", "ornith-ezzio", "modelfile"]:
        found = search_physical_tags(tag)
        print(f"  • Mot-clé [{tag}] trouvé dans {len(found)} fichiers :")
        for f in found[:5]:
            print(f"    - {f}")

    report = {
        "granite_references": search_physical_tags("ezzio-granite"),
        "ornith_references": search_physical_tags("ornith-ezzio"),
        "modelfile_references": search_physical_tags("modelfile")
    }
    
    out_file = PROJECT_ROOT / "tools" / "gate_v6_45_55_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n[+] Rapport d'arbitrage exporté : {out_file}")
    print("=" * 80)

if __name__ == "__main__":
    main()