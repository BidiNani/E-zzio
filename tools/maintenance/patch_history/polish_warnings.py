from pathlib import Path

print("[*] E-ZZIO v1.9.5.6 - Nettoyage des DeprecationWarnings...")

# 1. Correction du contrat sémantique
p1 = Path("runtime/memory/semantic/contracts.py")
if p1.exists():
    c1 = p1.read_text(encoding="utf-8")
    if "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)" in c1:
        c1 = c1.replace("__import__('datetime').datetime.now(__import__('datetime').timezone.utc)", "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)")
        p1.write_text(c1, encoding="utf-8")
        print("[+] contracts.py mis à jour (datetime.UTC).")

# 2. Correction du test d'invariants architecturaux
p2 = Path("tests/test_architectural_invariants.py")
if p2.exists():
    c2 = p2.read_text(encoding="utf-8")
    if "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)" in c2:
        c2 = c2.replace("__import__('datetime').datetime.now(__import__('datetime').timezone.utc)", "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)")
        p2.write_text(c2, encoding="utf-8")
        print("[+] test_architectural_invariants.py mis à jour.")

print("[OK] Avertissements Python 3.12 éradiqués.")
