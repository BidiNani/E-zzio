import os
import json
import re
from pathlib import Path

ROOT_PATH = Path(r"G:\AI\E-zzio")
AUDIT_DIR = ROOT_PATH / "runtime" / "audit" / "reliability"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

EXCLUDED_DIRS = {".venv", ".git", "__pycache__", "node_modules", "archive"}

def collect_files():
    files = []
    for root, dirs, filenames in os.walk(ROOT_PATH):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        for f in filenames:
            if f.endswith((".py", ".ps1", ".json", ".md")):
                files.append(Path(root) / f)
    return files

def run_audit():
    print("[*] Démarrage de l'audit de fiabilité natif Python...")
    all_files = collect_files()
    
    corpus = {}
    corpus_lower_paths = set()
    
    for file_path in all_files:
        rel_path = file_path.relative_to(ROOT_PATH).as_posix()
        corpus_lower_paths.add(rel_path.lower())
        try:
            corpus[rel_path] = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            corpus[rel_path] = ""

    dependency_graph = []
    broken_references = []

    import_regex = re.compile(r'^\s*(?:import|from)\s+([a-zA-Z0-9_\.]+)', re.MULTILINE)
    path_regex = re.compile(r'["\']([^"\']+\.(?:ps1|py|json))["\']')

    for path, content in corpus.items():
        if not content:
            continue
            
        ext = Path(path).suffix.lower()
        references = []

        if ext == ".py":
            for m in import_regex.finditer(content):
                mod_name = m.group(1).replace(".", "/")
                references.append(f"{mod_name}.py")
        elif ext in (".ps1", ".json"):
            for m in path_regex.finditer(content):
                references.append(m.group(1))

        for ref in references:
            clean_ref = ref.replace("\\", "/").lower()
            resolved = any(known.endswith(clean_ref) or clean_ref in known for known in corpus_lower_paths)

            dependency_graph.append({
                "source": path,
                "reference": ref,
                "resolved": resolved
            })

            ignored_libs = {"uvicorn", "psutil", "logging", "json", "pathlib", "urllib", "time", "os", "sys", "subprocess", "asyncio", "fastapi", "pydantic", "typing"}
            if not resolved and not any(ref.startswith(lib) for lib in ignored_libs):
                broken_references.append({
                    "source": path,
                    "reference": ref
                })

    (AUDIT_DIR / "dependency_graph.json").write_text(json.dumps(dependency_graph, indent=2), encoding="utf-8")
    (AUDIT_DIR / "broken_references.json").write_text(json.dumps(broken_references, indent=2), encoding="utf-8")

    print("\n=== SYNTHÈSE DE FIABILITÉ PYTHON ===")
    print(f"Total dépendances indexées : {len(dependency_graph)}")
    print(f"Références brisées : {len(broken_references)}")
    print(f"[OK] Rapports générés dans : {AUDIT_DIR}")

if __name__ == "__main__":
    run_audit()
