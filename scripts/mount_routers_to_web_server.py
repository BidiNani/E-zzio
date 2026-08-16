import re
from pathlib import Path

ROOT = Path(r"G:\AI\E-zzio")
web_server_file = ROOT / "web_server.py"

if not web_server_file.exists():
    print("[FAIL] web_server.py introuvable à la racine.")
    exit(1)

content = web_server_file.read_text(encoding="utf-8")

# Vérification si les imports sont déjà présents
if "runtime.routers.llm" not in content:
    imports_to_add = (
        "\nfrom runtime.routers.llm import router as llm_router\n"
        "from runtime.routers.mobile import router as mobile_router\n"
    )
    # Insertion des imports juste sous l'instanciation FastAPI ou en haut des imports
    if "app = FastAPI(" in content:
        content = content.replace("app = FastAPI(", imports_to_add + "app = FastAPI(")
    else:
        content = imports_to_add + content

# Vérification du montage des routeurs
mounts_to_add = (
    "\napp.include_router(llm_router)\n"
    "app.include_router(mobile_router)\n"
)

if "app.include_router(llm_router)" not in content:
    if "if __name__ ==" in content:
        content = content.replace("if __name__ ==", mounts_to_add + "\nif __name__ ==")
    else:
        content += mounts_to_add

web_server_file.write_text(content, encoding="utf-8")
print("[OK] Routeurs llm.py et mobile.py montés dans web_server.py.")
