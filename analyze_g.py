import os
import json
from pathlib import Path

ROOT_G = Path("G:\\")
REPORT_PATH = Path("G:/AI/E-zzio/memory/g_drive_analysis.json")

def analyze_g_drive():
    if not ROOT_G.exists():
        return {"error": "Le lecteur G:\\ n'est pas accessible directement depuis cet environnement."}
    
    summary = {
        "total_folders": 0,
        "total_files": 0,
        "ai_projects": [],
        "models_or_weights": [],
        "large_folders": {}
    }
    
    try:
        entries = list(ROOT_G.iterdir())
        for entry in entries:
            if entry.is_dir():
                summary["total_folders"] += 1
                dir_name = entry.name
                # Détection des projets IA majeurs
                if any(keyword in dir_name.lower() for keyword in ["ai", "bao", "bidi", "ezzio", "wiki"]):
                    summary["ai_projects"].append(dir_name)
                
                # Comptage rapide des fichiers du sous-dossier
                try:
                    file_count = sum(1 for _ in entry.rglob('*') if _.is_file())
                    summary["large_folders"][dir_name] = file_count
                    summary["total_files"] += file_count
                except Exception:
                    pass
            elif entry.is_file():
                summary["total_files"] += 1

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    res = analyze_g_drive()
    print("📊 RÉSULTAT DE L'ANALYSE G:\\ :")
    print(json.dumps(res, ensure_ascii=False, indent=2))