import json
from pathlib import Path
from collections import defaultdict

class DependencyIntelligenceAnalyzer:
    def __init__(self, scan_dir: Path):
        self.scan_dir = scan_dir
        self.inventory = json.loads((scan_dir / "inventory.json").read_text(encoding="utf-8"))
        self.symbols = json.loads((scan_dir / "python_symbols.json").read_text(encoding="utf-8"))
        self.imports_graph = json.loads((scan_dir / "imports_graph.json").read_text(encoding="utf-8"))

    def compute_scores(self):
        print("[*] Calcul des scores d'autorité et cartographie des dépendances...")

        # 1. Calcul des dépendants entrants (qui importe quoi)
        dependents_map = defaultdict(list)
        for file_path, imports in self.imports_graph.items():
            for imp in imports:
                # Recherche grossière de correspondance par nom de module
                for item in self.inventory:
                    if item["type"] == "py":
                        mod_name = Path(item["path"]).stem
                        if mod_name == imp or imp in item["path"]:
                            dependents_map[item["path"]].append(file_path)

        analysis_results = {}

        for item in self.inventory:
            if item["type"] != "py":
                continue
            
            path = item["path"]
            syms = self.symbols.get(path, {"classes": [], "functions": [], "imports": []})
            if "error" in syms:
                continue

            incoming_deps = list(set(dependents_map.get(path, [])))
            outgoing_imports = syms.get("imports", [])
            classes_count = len(syms.get("classes", []))
            funcs_count = len(syms.get("functions", []))

            # Calcul d'un score d'autorité heuristique
            score = 10
            if "core/" in path: score += 50
            if "runtime/hardware/trust/" in path: score += 40
            score += len(incoming_deps) * 15
            score += classes_count * 3
            score += funcs_count

            # Malus pour les anciens prototypes ou chemins isolés
            if "models_governance" in path or "legacy" in path:
                score = max(5, score - 60)

            analysis_results[path] = {
                "role": item["role_detected"],
                "incoming_dependents_count": len(incoming_deps),
                "incoming_dependents": incoming_deps,
                "outgoing_imports_count": len(outgoing_imports),
                "classes_count": classes_count,
                "functions_count": funcs_count,
                "authority_score": min(100, score)
            }

        # Tri par score d'autorité décroissant
        sorted_analysis = dict(sorted(analysis_results.items(), key=lambda x: x[1]["authority_score"], reverse=True))

        report_path = self.scan_dir / "dependency_analysis_report.json"
        report_path.write_text(json.dumps(sorted_analysis, indent=2, ensure_ascii=False), encoding="utf-8")
        
        print(f"[OK] Rapport d'intelligence des dépendances généré : {report_path}")
        
        # Affichage du top 5 des modules à haute autorité
        print("\n--- TOP 5 DES MODULES À HAUTE AUTORITÉ ---")
        for path, data in list(sorted_analysis.items())[:5]:
            print(f"  [{data['authority_score']}/100] {path} (Dépendants: {data['incoming_dependents_count']})")

        # Affichage des doublons ou modules faibles suspects
        print("\n--- CANDIDATS SUSPECTS / FAIBLE AUTORITÉ ---")
        for path, data in sorted_analysis.items():
            if data['authority_score'] < 25 and data['incoming_dependents_count'] == 0:
                print(f"  [{data['authority_score']}/100] {path} (Aucun dépendant détecté)")

if __name__ == "__main__":
    analyzer = DependencyIntelligenceAnalyzer(Path("runtime/audit/intelligence_scan"))
    analyzer.compute_scores()
