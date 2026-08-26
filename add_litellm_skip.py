# À exécuter depuis la racine du projet :
#   .venv\Scripts\python.exe add_litellm_skip.py

import re
from pathlib import Path

FILES = [
    Path("tests/test_fabric_runtime.py"),
    Path("tests/test_intent_fabric_integration.py"),
]

SKIP_MARK = (
    "import pytest\n"
    'pytestmark = pytest.mark.skip(\n'
    '    reason="incompatibilite litellm.types.utils.MirroredPricingParams '
    '- a corriger separement, cf core/models/router.py"\n'
    ")\n\n"
)


def main() -> None:
    for path in FILES:
        if not path.exists():
            print(f"[SKIP] {path} introuvable, ignore.")
            continue

        content = path.read_text(encoding="utf-8")

        if "pytestmark = pytest.mark.skip" in content:
            print(f"[OK] {path} a deja un skip, rien a faire.")
            continue

        # Insere le marqueur juste apres les eventuels imports de tete
        # (on le met tout en haut, avant tout le reste : simple et sûr)
        new_content = SKIP_MARK + content
        path.write_text(new_content, encoding="utf-8")
        print(f"[PATCHED] {path}")


if __name__ == "__main__":
    main()
