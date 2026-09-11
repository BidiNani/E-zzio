"""
E-ZZIO V7.59.9 — Active Runtime Convergence Test
Trace récursivement les dépendances depuis le point d'entrée du boot (core/runtime/boot.py)
et mesure la convergence avec le manifeste founding_kernel.json.
"""

import json
import re
from pathlib import Path

ROOT_DIR = Path(r"G:\AI\E-zzio")
KERNEL_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "founding_kernel.json"
BOOT_ENTRY = ROOT_DIR / "core" / "runtime" / "boot.py"
OUTPUT_REPORT = ROOT_DIR / "runtime" / "audit" / "system" / "runtime_convergence_report.json"


def get_module_imports(file_path: Path) -> set:
    imports = set()
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_stripped = line.strip()
                if match := re.match(r"^(?:import|from)\s+([a-zA-Z0-9_\.]+)", line_stripped):
                    parts = match.group(1).split(".")
                    # Résolution des modules internes core ou runtime
                    if parts[0] in {"core", "runtime"}:
                        imports.add("/".join(parts))
    except Exception:
        pass
    return imports


def trace_active_runtime() -> set:
    visited = set()
    queue = []

    if BOOT_ENTRY.exists():
        queue.append(BOOT_ENTRY)
        visited.add("core/runtime/boot.py")
    else:
        # Fallback sur l'intelligence router si boot.py n'est pas la cible directe
        fallback = ROOT_DIR / "core" / "intelligence_router.py"
        if fallback.exists():
            queue.append(fallback)
            visited.add("core/intelligence_router.py")

    active_modules = set(visited)

    while queue:
        current_file = queue.pop(0)
        file_imports = get_module_imports(current_file)

        for imp in file_imports:
            # Chercher le fichier .py correspondant sur disque
            for ext in ["", ".py", "/__init__.py"]:
                candidate_rel = imp + ext
                candidate_path = ROOT_DIR / candidate_rel
                if candidate_path.exists() and candidate_rel not in active_modules:
                    active_modules.add(candidate_rel)
                    if candidate_path.is_file() and candidate_path.suffix == ".py":
                        queue.append(candidate_path)
                    break
    return active_modules


def run_convergence_test():
    print("[*] Évaluation de la convergence active du runtime...")

    if not KERNEL_REPORT.exists():
        print("[!] Erreur : Manifeste founding_kernel.json introuvable. Exécutez V7.59.8 d'abord.")
        return

    with open(KERNEL_REPORT, "r", encoding="utf-8") as f:
        kernel_data = json.load(f)

    kernel_modules = {item["module"] for item in kernel_data["full_kernel_registry"]}
    active_runtime_modules = trace_active_runtime()

    # Calcul du croisement (Intersection vs Union)
    converged = kernel_modules.intersection(active_runtime_modules)
    orphaned_kernel = kernel_modules - active_runtime_modules
    unmapped_active = active_runtime_modules - kernel_modules

    convergence_rate = round((len(converged) / len(kernel_modules)) * 100, 2) if kernel_modules else 0.0

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat() if "datetime" in globals() else "2026-08-12",
        "total_kernel_modules": len(kernel_modules),
        "total_active_boot_modules": len(active_runtime_modules),
        "converged_modules_count": len(converged),
        "convergence_rate_percent": convergence_rate,
        "orphaned_kernel_modules": list(orphaned_kernel),
        "unmapped_active_modules": list(unmapped_active),
    }

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print(" ACTIVE RUNTIME CONVERGENCE REPORT (V7.59.9)")
    print("=" * 65)
    print(f" Modules du noyau recensés     : {len(kernel_modules)}")
    print(f" Modules actifs au démarrage   : {len(active_runtime_modules)}")
    print(f" Modules convergents (liés)    : {len(converged)}")
    print(f" Taux de convergence active    : {convergence_rate}%")
    print("-" * 65)
    print(f" Nœuds dormants / isolés       : {len(orphaned_kernel)}")
    print("=" * 65)
    print(f" Rapport exporté : {OUTPUT_REPORT}")


if __name__ == "__main__":
    from datetime import datetime, timezone

    run_convergence_test()
