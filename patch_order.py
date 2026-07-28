from pathlib import Path

p = Path("runtime/action/store.py")

code = p.read_text(encoding="utf-8")

code = code.replace(
    "ORDER BY rowid DESC",
    "ORDER BY timestamp DESC, rowid DESC"
)

p.write_text(code, encoding="utf-8")

print("[OK] Tri ledger corrigé")
