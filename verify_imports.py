"""
Vérification des imports de la chaîne agentique E-zzio.
À lancer depuis la racine du projet (G:\\AI\\E-zzio), avec le venv du projet activé :

    cd G:\\AI\\E-zzio
    .venv\\Scripts\\python.exe verify_imports.py

Ce script ne modifie rien. Il essaie juste d'importer chaque module de la chaîne
et rapporte précisément lequel casse et pourquoi (souvent un import mort vers
un fichier supprimé lors de la purge : server.py, bot.py, skill_manager.py...).
"""

import importlib
import sys
import traceback

# Adapte cette liste si les noms de module réels diffèrent légèrement
# (ex: core.agent.coding_agent_loop vs core.agent.coding_agent_harness)
MODULES_TO_CHECK = [
    "core.agent.coding_agent_loop",
    "core.agent.agent_provider",
    "core.agent.agent_guard",
    "core.agent.patch_engine",
    "core.agent.tools_registry",
    "core.agent.codebase_indexer",
]


def check_module(module_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module_name)
        return True, "OK"
    except Exception as exc:  # noqa: BLE001 - on veut tout capturer ici
        tb = traceback.format_exc()
        return False, f"{type(exc).__name__}: {exc}\n{tb}"


def main() -> int:
    print("=" * 70)
    print("VERIFICATION DES IMPORTS - CHAINE AGENTIQUE E-ZZIO")
    print("=" * 70)

    results = {}
    for module_name in MODULES_TO_CHECK:
        ok, detail = check_module(module_name)
        results[module_name] = (ok, detail)
        status = "OK" if ok else "ECHEC"
        print(f"[{status}] {module_name}")
        if not ok:
            print(f"    -> {detail.splitlines()[0]}")

    print("=" * 70)
    failures = [name for name, (ok, _) in results.items() if not ok]

    if not failures:
        print("Tous les modules s'importent correctement.")
        return 0

    print(f"{len(failures)} module(s) en echec sur {len(results)}.")
    print("Detail complet des echecs :\n")
    for name in failures:
        _, detail = results[name]
        print(f"--- {name} ---")
        print(detail)
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
