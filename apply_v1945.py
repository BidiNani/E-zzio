from pathlib import Path

print("[*] E-ZZIO v1.9.4.5 — Application du correctif robuste TokenSigner...")

# ------------------------------------------------------------------------------
# 1. Correction chirurgicale et robuste de microkernel.py
# ------------------------------------------------------------------------------
micro_path = Path("runtime/core/microkernel.py")
lines = micro_path.read_text(encoding="utf-8").splitlines()

# Nettoyage de tout ancien import erroné potentiellement présent
lines = [l for l in lines if "runtime.security.signer" not in l and "SecuritySigner" not in l]

# S'assurer que TokenSigner est importé
has_token_signer_import = any("TokenSigner" in line for line in lines)
if not has_token_signer_import:
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_idx = i + 1
    lines.insert(insert_idx, "from runtime.contracts.capability import TokenSigner")
    print("[+] Import de TokenSigner ajouté.")

# S'assurer que self.signer = TokenSigner() est présent dans __init__
has_self_signer = any("self.signer =" in line for line in lines)
if not has_self_signer:
    new_lines = []
    in_init = False
    injected = False
    for line in lines:
        new_lines.append(line)
        if "def __init__" in line:
            in_init = True
        elif in_init and "self.key_manager = key_manager" in line:
            indent = line[:line.index("self.key_manager")]
            new_lines.append(f"{indent}self.signer = TokenSigner()")
            injected = True
            in_init = False
        elif in_init and line.strip().startswith("def "):
            in_init = False
    
    if injected:
        lines = new_lines
        print("[+] self.signer = TokenSigner() injecté dans __init__.")
    else:
        print("[!] Avertissement : self.key_manager introuvable dans __init__.")

micro_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

# ------------------------------------------------------------------------------
# 2. Écriture propre du test de wiring (tests/test_executor_wiring.py)
# ------------------------------------------------------------------------------
wiring_test_path = Path("tests/test_executor_wiring.py")
wiring_code = """import pytest
from runtime.tools.executors.powershell import PowerShellExecutor
from runtime.tools.executors.filesystem import FileSystemExecutor

def test_executor_module_wiring():
    \"\"\"Vérifie que les exécuteurs officiels respectent les contrats d'intégrité architecturale.\"\"\"
    assert PowerShellExecutor.execute.__module__ == "runtime.tools.executors.powershell"
    assert FileSystemExecutor.execute.__module__ == "runtime.tools.executors.filesystem"
"""
wiring_test_path.write_text(wiring_code.strip() + "\n", encoding="utf-8")
print("[+] test_executor_wiring.py réécrit proprement.")
print("[OK] Préparation terminée avec succès.")
