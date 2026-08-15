"""
E-ZZIO V7.59.4.1 — RPG Qualification Probe
Extrait des fenêtres de contexte (20 lignes) autour des marqueurs RPG dans les fichiers suspects.
Analyse en lecture seule pour différencier une "Connaissance" d'un "Inventaire technique".
"""
from pathlib import Path
import json

ROOT_DIR = Path(r"G:\AI\E-zzio")
TARGET_FILE = ROOT_DIR / "tools/maintenance/logs/dump_complet.txt"
OUTPUT_REPORT = ROOT_DIR / "runtime/audit/system/rpg_memory_qualification.json"

RPG_KEYWORDS = ["wotlk", "druid", "feral", "raid", "macro", "talent", "gear", "instance"]

def qualify():
    if not TARGET_FILE.exists():
        print(f"[!] Erreur : Fichier cible introuvable : {TARGET_FILE}")
        return

    print(f"[*] Analyse forensique de : {TARGET_FILE.name}")
    
    findings = []
    
    with open(TARGET_FILE, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in RPG_KEYWORDS):
            # Extraction fenêtre de contexte +/- 20 lignes
            start = max(0, i - 20)
            end = min(len(lines), i + 21)
            context = "".join(lines[start:end])
            
            findings.append({
                "line_number": i,
                "trigger_line": line.strip(),
                "context": context
            })

    # Sauvegarde des résultats pour analyse
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)

    print(f"[*] Audit terminé. {len(findings)} fenêtres de contexte extraites.")
    print(f"[*] Rapport disponible : {OUTPUT_REPORT}")
    
    # Aperçu rapide console
    for f in findings[:3]:
        print(f"\n--- Contexte (Ligne {f['line_number']}) ---")
        print(f"{f['trigger_line'][:80]}...")

if __name__ == "__main__":
    qualify()
