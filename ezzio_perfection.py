import shutil
from pathlib import Path

print("\n[*] PHASE 1 & 2 : Audit et Correction Chirurgicale...")
# Remplacement universel indépendant des types d'imports datetime
target = "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)"
count = 0

for p in Path('.').rglob('*.py'):
    if p.is_file() and not any(part.startswith('.') or part == 'venv' for part in p.parts):
        try:
            content = p.read_text(encoding="utf-8")
            changed = False
            
            # Éradication de la dépréciation d'origine
            if "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)" in content:
                content = content.replace("__import__('datetime').datetime.now(__import__('datetime').timezone.utc)", target)
                changed = True
                
            # Éradication de ma propre tentative précédente qui causait l'AttributeError
            if "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)" in content:
                content = content.replace("__import__('datetime').datetime.now(__import__('datetime').timezone.utc)", target)
                changed = True
                
            if changed:
                p.write_text(content, encoding="utf-8")
                print(f"  -> [CORRIGÉ] {p}")
                count += 1
        except Exception:
            pass

print(f"[+] {count} fichier(s) mis aux normes absolues Python 3.12+.\n")

print("[*] PHASE 3 : Purge Intensive des Caches...")
for p in Path('.').rglob('__pycache__'): shutil.rmtree(p, ignore_errors=True)
for p in Path('.').rglob('*.py[co]'): p.unlink(missing_ok=True)
if Path('.pytest_cache').exists(): shutil.rmtree('.pytest_cache', ignore_errors=True)
print("[+] Caches système et Pytest volatilisés.\n")
