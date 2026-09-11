from pathlib import Path

p = Path(r"G:\AI\E-zzio\runtime\model_router\router.py")
txt = p.read_text(encoding="utf-8")

# 1. Normalisation de request
old = """        if not isinstance(request, dict):
            request = {}
        request.update(kwargs)
        task = request.get('task', 'general')"""

new = """        # Normalisation : support dict, Pydantic, objets
        if hasattr(request, "model_dump"):
            request = request.model_dump()
        elif hasattr(request, "__dict__"):
            request = vars(request)
        elif not isinstance(request, dict):
            request = {}

        request.update(kwargs)

        # Extraction du prompt
        prompt = request.get("prompt") or request.get("content")
        if not prompt:
            raise ValueError("Requête LLM invalide : prompt absent")

        task = request.get('task', 'general')"""

if old in txt:
    txt = txt.replace(old, new)
    print("[OK] Normalisation request corrigée")
else:
    print("[FAIL] Bloc normalisation introuvable")

# 2. Correction appel provider
old2 = "prompt=request['prompt'],"
new2 = "prompt=prompt,"

if old2 in txt:
    txt = txt.replace(old2, new2)
    print("[OK] Appel provider corrigé")
else:
    print("[FAIL] Appel provider introuvable")

p.write_text(txt, encoding="utf-8")
print("[OK] Router patché avec succès")
