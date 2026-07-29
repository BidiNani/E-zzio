from pathlib import Path
import re

print("[*] Analyse registry.py")


path = Path("runtime/action/registry.py")

code = path.read_text(encoding="utf-8")


# Vérifie si le patch existe déjà
if "SELF_HEAL_BLOCKED_LEDGER" in code:
    print("[!] Patch déjà présent")
    exit(0)


marker = "# SELF_HEAL_BLOCKED_LEDGER"


# Cas permission denied
pattern = (
r'(\s*)(res = \{"status": "BLOCKED", "error": f"Permission denied for action.*?\}\})'
)


replacement = r'''\1\2

\1# SELF_HEAL_BLOCKED_LEDGER
\1try:
\1    self.store.log_execution(
\1        exec_id,
\1        name,
\1        "BLOCKED",
\1        payload,
\1        res,
\1        cost,
\1        0.0
\1    )
\1except Exception as ledger_error:
\1    print(
\1        f"[SELF-HEAL] Ledger write protection bypass : {ledger_error}"
\1    )
'''


new_code, count = re.subn(
    pattern,
    replacement,
    code,
    flags=re.DOTALL
)


if count == 0:

    print("[!] Aucun bloc permission trouvé")

    # Recherche générique autour des retours BLOCKED
    if "Permission denied for action" not in code:
        raise RuntimeError(
            "Impossible de localiser le bloc Permission BLOCKED"
        )


else:

    code = new_code


path.write_text(
    code,
    encoding="utf-8"
)


print(
    f"[OK] Patch appliqué : {count} bloc(s)"
)

