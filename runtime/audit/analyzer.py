import json
from pathlib import Path

class EzzioSemanticAnalyzer:
    def __init__(self, scan_dir: Path):
        self.scan_dir = scan_dir
        self.inventory = json.loads((scan_dir / "inventory.json").read_text(encoding="utf-8"))
        self.symbols = json.loads((scan_dir / "python_symbols.json").read_text(encoding="utf-8"))
        self.configs = json.loads((scan_dir / "configs_inventory.json").read_text(encoding="utf-8"))
        
        self.classification = {}
        self.duplicates = []

    def classify_and_detect(self):
        print("[*] Analyse intelligente des composants en cours...")
        
        # Regroupement par nom de fichier de base pour détecter les doublons potentiels
        name_buckets = {}

        for item in self.inventory:
            path_str = item["path"]
            filename = Path(path_str).name
            
            # Classification heuristique
            category = self._heuristic_category(path_str)
            importance = self._heuristic_importance(path_str, category)
            
            self.classification[path_str] = {
                "category": category,
                "importance": importance,
                "status": "KEEP" if importance != "LEGACY" else "REVIEW"
            }

            # Bucket pour doublons par nom
            if filename not in name_buckets:
                name_buckets[filename] = []
            name_buckets[filename].append(path_str)

        # Détection des candidats doublons (même nom ou pattern proche)
        for filename, paths in name_buckets.items():
            if len(paths) > 1:
                self.duplicates.append({
                    "group": filename.upper().replace(".", "_"),
                    "files": paths,
                    "recommendation": "MERGE_OR_ARCHIVE"
                })

        # Sauvegarde des rapports d'analyse
        (self.scan_dir / "classification.json").write_text(json.dumps(self.classification, indent=2, ensure_ascii=False), encoding="utf-8")
        (self.scan_dir / "duplicate_candidates.json").write_text(json.dumps(self.duplicates, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[OK] Analyse terminée. {len(self.duplicates)} groupes de doublons potentiels identifiés.")

    def _heuristic_category(self, path: str) -> str:
        p = path.lower()
        if "core" in p: return "CORE"
        if "runtime/hardware/trust" in p: return "TRUST"
        if "runtime/hardware" in p: return "RUNTIME"
        if "guardian" in p: return "SECURITY"
        if "test" in p or "bench" in p: return "TEST"
        if "tool" in p: return "TOOLS"
        if "legacy" in p or "old" in p: return "LEGACY"
        if "experiment" in p: return "EXPERIMENTAL"
        if any(k in p for k in ["model", "contract", "registry"]): return "MODEL"
        return "UNKNOWN"

    def _heuristic_importance(self, path: str, category: str) -> str:
        if category in ["CORE", "TRUST", "SECURITY"]: return "CRITICAL"
        if category in ["LEGACY", "EXPERIMENTAL"]: return "LEGACY"
        if category == "TEST": return "SUPPORT"
        return "NORMAL"

if __name__ == "__main__":
    analyzer = EzzioSemanticAnalyzer(Path("runtime/audit/full_scan"))
    analyzer.classify_and_detect()
