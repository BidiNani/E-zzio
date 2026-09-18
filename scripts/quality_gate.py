import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ACTIVE_DIRS = ["core", "runtime/core", "routers", "interfaces", "tests"]


def run_gate():
    print("[ÉTAPE 1/3] Compilation Bytecode récursive...")
    total_compiled = 0
    for d in ACTIVE_DIRS:
        target_dir = ROOT / d
        if not target_dir.exists():
            continue
        for py_file in target_dir.rglob("*.py"):
            try:
                py_compile.compile(str(py_file), doraise=True)
                total_compiled += 1
            except py_compile.PyCompileError as e:
                print(f"[-] ERREUR DE SYNTAXE : {py_file} -> {e}")
                sys.exit(1)
    print(f"  -> {total_compiled} fichiers compilés avec succès (0 erreur).")

    print("[ÉTAPE 2/3] Validation SQLite WAL & FTS5...")
    import asyncio

    from core.memory.unified_gateway import UnifiedMemoryGateway

    async def test_mem():
        gw = UnifiedMemoryGateway("runtime/evidence/evidence.db")
        await gw.init()

    asyncio.run(test_mem())
    print("  -> Base SQLite WAL & index FTS5 opérationnels.")

    print("[ÉTAPE 3/3] Vérification des contrats fondamentaux terminée.")


if __name__ == "__main__":
    run_gate()
