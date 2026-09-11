from pathlib import Path

p = Path(r"G:\AI\E-zzio\runtime\model_router\router.py")
txt = p.read_text(encoding="utf-8")

# Remplacer la signature generate()
old = """    def generate(self, request: Dict[str, Any]) -> Dict[str, Any]:"""
new = """    def generate(self, request=None, **kwargs) -> Dict[str, Any]:
        # Compatibilité API E-ZZIO
        if request is None:
            request = {}
        if not isinstance(request, dict):
            request = {}
        request.update(kwargs)"""

if old in txt:
    txt = txt.replace(old, new)
    p.write_text(txt, encoding="utf-8")
    print("[OK] router.generate() patché")
else:
    print("[FAIL] Bloc generate introuvable")
