#!/usr/bin/env python3
"""
E-ZZIO — Amorçage de la couche identité (runtime/identity/).

Pourquoi ce script existe
-------------------------
`core/identity/canonical_identity.py` est volontairement *fail-closed* : sans
`runtime/identity/persona.hash` et `runtime/identity/persona.full.md`, il lève
une RuntimeError dès la construction du prompt système. C'est le bon
comportement pour la production.

Mais `runtime/` est gitignoré (voir .gitignore), donc ces fichiers disparaissent
et **un clone propre ne peut pas démarrer**. Le symptôme est un
`RuntimeError: [IDENTITY FAIL-CLOSED] Source requise absente` que rien n'explique.

Ce script régénère la couche depuis les sources SUIVIES par git :

    config/persona.json      (traits, version kernel)  -> hash de contrat
    registry/persona.txt     (la persona longue)        -> persona.full.md
    core/identity/canonical_identity.py (constantes)    -> identity.json

Il ne contourne aucune vérification : `persona.hash` est le SHA-256 réel de
`config/persona.json`. Modifier la persona sans régénérer le hash fera à nouveau
échouer `_verify_integrity()`, ce qui est le but.

Usage :
    python tools/bootstrap_identity.py          # genere
    python tools/bootstrap_identity.py --check  # verifie sans ecrire
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUNTIME_IDENTITY = ROOT / "runtime" / "identity"
PERSONA_JSON = ROOT / "config" / "persona.json"
PERSONA_TXT = ROOT / "registry" / "persona.txt"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def build_identity_json() -> dict:
    """Reprend les constantes de CanonicalIdentity sans les dupliquer a la main."""
    from core.identity.canonical_identity import CanonicalIdentity

    payload = CanonicalIdentity(root_dir=ROOT).get_payload()
    persona_meta: dict = {}
    if PERSONA_JSON.is_file():
        try:
            persona_meta = json.loads(PERSONA_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"[ERREUR] config/persona.json illisible : {exc}") from exc
    return {
        "contract": payload,
        "persona_meta": persona_meta,
        "source": "registry/persona.txt",
    }


def check() -> int:
    """Verifie que la couche identite existe et que le hash est coherent."""
    problems: list[str] = []
    for rel in ("persona.hash", "persona.full.md", "identity.json", "identity_authority.json"):
        if not (RUNTIME_IDENTITY / rel).is_file():
            problems.append(f"absent : runtime/identity/{rel}")

    if PERSONA_JSON.is_file() and (RUNTIME_IDENTITY / "persona.hash").is_file():
        expected = sha256_file(PERSONA_JSON)
        stored = (RUNTIME_IDENTITY / "persona.hash").read_text(encoding="utf-8").strip().lower()
        if expected != stored:
            problems.append(
                f"hash incoherent : persona.hash={stored} config/persona.json={expected}"
            )

    if problems:
        print("[IDENTITE] INCOMPLETE")
        for p in problems:
            print(f"  - {p}")
        print("\n  Regenerer avec : python tools/bootstrap_identity.py")
        return 1

    print("[IDENTITE] OK — couche presente et hash coherent")
    return 0


def generate() -> int:
    if not PERSONA_JSON.is_file():
        raise SystemExit(f"[ERREUR] source introuvable : {PERSONA_JSON}")
    if not PERSONA_TXT.is_file():
        raise SystemExit(f"[ERREUR] source introuvable : {PERSONA_TXT}")

    RUNTIME_IDENTITY.mkdir(parents=True, exist_ok=True)

    # 1. hash de contrat = SHA-256 du fichier persona.json suivi par git
    digest = sha256_file(PERSONA_JSON)
    (RUNTIME_IDENTITY / "persona.hash").write_text(digest + "\n", encoding="utf-8")

    # 2. persona longue, depuis la source suivie
    persona = PERSONA_TXT.read_text(encoding="utf-8", errors="strict").strip()
    (RUNTIME_IDENTITY / "persona.full.md").write_text(persona + "\n", encoding="utf-8")

    # 3. identite compilee
    identity = build_identity_json()
    (RUNTIME_IDENTITY / "identity.json").write_text(
        json.dumps(identity, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # 4. autorite identitaire : qui fait autorite, ou va la donnee
    authority = {
        "mentor": identity["contract"]["mentor"],
        "mother_reference": identity["contract"]["mother_reference"],
        "execution_authority": identity["contract"]["policy"]["execution_authority"],
        "fail_closed_on_integrity_error": identity["contract"]["policy"][
            "fail_closed_on_integrity_error"
        ],
        "persona_hash": digest,
        "persona_source": "registry/persona.txt",
        "note": (
            "L'identite decrit QUI est E-ZZIO, jamais CE QU'il peut faire. "
            "L'autorite d'execution reste core/kernel/native_harness.py."
        ),
    }
    (RUNTIME_IDENTITY / "identity_authority.json").write_text(
        json.dumps(authority, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("[IDENTITE] couche genere dans runtime/identity/")
    for f in sorted(RUNTIME_IDENTITY.iterdir()):
        print(f"  {f.name} ({f.stat().st_size} o)")
    print(f"\n  persona.hash = {digest}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Amorce la couche identite E-ZZIO")
    ap.add_argument("--check", action="store_true", help="verifie sans ecrire")
    args = ap.parse_args()
    return check() if args.check else generate()


if __name__ == "__main__":
    raise SystemExit(main())
