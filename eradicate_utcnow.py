import re
import shutil
from pathlib import Path

print("\n[*] PHASE 1 : Détection et Correction par Expression Régulière...")

target_call = "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)"
target_lambda = f"lambda: {target_call}"

patched_files = 0

for p in Path('.').rglob('*.py'):
    if p.is_file() and not any(part.startswith('.') or part == 'venv' for part in p.parts):
        try:
            content = p.read_text(encoding="utf-8")
            if "utcnow" not in content and "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)" not in content:
                continue
                
            old_content = content
            
            # 1. Remplacement des default_factory=lambda: __import__('datetime').datetime.now(__import__('datetime').timezone.utc) (ou __import__('datetime').datetime.now(__import__('datetime').timezone.utc))
            content = re.sub(
                r'default_factory\s*=\s*(?:datetime\.)?datetime\.utcnow',
                f'default_factory={target_lambda}',
                content
            )
            
            # 2. Remplacement des appels directs __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
            content = re.sub(
                r'(?:datetime\.)?datetime\.utcnow\(\)',
                target_call,
                content
            )
            
            # 3. Remplacement des références orphelines __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
            content = re.sub(
                r'(?:datetime\.)?datetime\.utcnow',
                target_call,
                content
            )
            
            # 4. Nettoyage des syntaxe invalides précédentes
            content = content.replace("__import__('datetime').datetime.now(__import__('datetime').timezone.utc)", target_call)

            if content != old_content:
                p.write_text(content, encoding="utf-8")
                print(f"  -> [CORRIGÉ AVEC SUCCÈS] {p}")
                patched_files += 1

        except Exception as e:
            print(f"  [-] Erreur sur {p}: {e}")

print(f"[+] Total : {patched_files} fichier(s) mis aux normes absolues Python 3.12+.\n")

print("[*] PHASE 2 : Purge Totale des Caches...")
for p in Path('.').rglob('__pycache__'): shutil.rmtree(p, ignore_errors=True)
for p in Path('.').rglob('*.py[co]'): p.unlink(missing_ok=True)
if Path('.pytest_cache').exists(): shutil.rmtree('.pytest_cache', ignore_errors=True)
print("[+] Caches purgés avec succès.\n")
