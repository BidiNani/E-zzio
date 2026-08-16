import json
from pathlib import Path

class DependencyImpactScanner:
    def __init__(self, scan_dir: Path):
        self.scan_dir = scan_dir
        self.imports_path = scan_dir / "full_scan" / "imports_graph.json"
        self.inventory_path = scan_dir / "full_scan" / "inventory.json"

    def analyze_impact(self):
        print("[*] Analyse d'impact des dépendances en cours...")
        
        if not self.imports_path.exists() or not self.inventory_path.exists():
            print("[ERR] Artefacts de scan introuvables. Exécutez d'abord le scanner de Phase 1.")
            return

        imports_graph = json.loads(self.imports_path.read_text(encoding="utf-8"))
        
        # Cibles critiques identifiées lors du filtrage précédent
        targets_of_interest = [
            "model_registry",
            "models_governance",
            "governor",
            "resolver",
            "supervisor"
        ]

        impact_report = {}

        for target in targets_of_interest:
            dependents = []
            for file_path, imported_modules in imports_graph.items():
                # Vérifie si le fichier importe ou référence un module cible
                if any(target in mod.lower() for mod in imported_modules):
                    dependents.append(file_path)
                else:
                    # Vérification textuelle brute pour les imports relatifs ou dynamiques
                    try:
                        content = Path(file_path).read_text(encoding="utf-8")
                        if target in content and f"core/{target}" not in file_path and f"trust/{target}" not in file_path:
                            if file_path not in dependents:
                                dependents.append(file_path)
                    except Exception:
                        pass
            
            impact_report[target] = {
                "referenced_by_count": len(dependents),
                "dependents": dependents
            }

        # Sauvegarde du rapport d'impact
        report_path = self.scan_dir / "dependency_impact.json"
        report_path.write_text(json.dumps(impact_report, indent=2, ensure_ascii=False), encoding="utf-8")
        
        print(f"\n[OK] Rapport d'impact généré : {report_path}")
        for target, data in impact_report.items():
            print(f"  - Cible '{target}': référencé par {data['referenced_by_count']} fichier(s)")
            for dep in data["dependents"][:5]:  # Afficher les 5 premiers
                print(f"      <- {dep}")
            if data["referenced_by_count"] > 5:
                print(f"      ... et {data['referenced_by_count'] - 5} autres.")

if __name__ == "__main__":
    scanner = DependencyImpactScanner(Path("runtime/audit"))
    scanner.analyze_impact()
