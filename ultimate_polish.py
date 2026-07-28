import shutil
from pathlib import Path

print("[*] E-ZZIO v1.9.5.7 - Éradication chirurgicale des Warnings Datetime...")

# 1. Purge des caches pour éviter tout faux positif
for p in Path('.').rglob('__pycache__'): shutil.rmtree(p, ignore_errors=True)
for p in Path('.').rglob('*.pyc'): p.unlink(missing_ok=True)

# 2. Remplacement universel et foolproof (anti-plantage d'import)
target_replacement = "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)"

files_patched = 0
for p in Path('.').rglob('*.py'):
    if p.is_file():
        try:
            content = p.read_text(encoding="utf-8")
            changed = False
            
            # Correction de ma propre erreur du script précédent
            if "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)" in content:
                content = content.replace("__import__('datetime').datetime.now(__import__('datetime').timezone.utc)", target_replacement)
                changed = True
                
            # Éradication du warning DeprecationWarning natif
            if "__import__('datetime').datetime.now(__import__('datetime').timezone.utc)" in content:
                content = content.replace("__import__('datetime').datetime.now(__import__('datetime').timezone.utc)", target_replacement)
                changed = True
                
            if changed:
                p.write_text(content, encoding="utf-8")
                print(f"[+] {p} nettoyé avec succès.")
                files_patched += 1
        except Exception:
            pass

print(f"[OK] {files_patched} fichier(s) mis à jour vers les standards Python 3.12+.")
