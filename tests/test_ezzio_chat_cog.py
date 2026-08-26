#!/usr/bin/env python3
"""Validation unitaire de l'agent Discord E-zzio."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from omnipresence.cogs.chat_cog import EzzioChatCog

load_dotenv(PROJECT_ROOT / "secrets" / ".env", override=True)


async def main() -> None:
    print("=== Démarrage du banc d'essai unitaire : EzzioChatCog ===")
    mock_bot = MagicMock()
    cog = EzzioChatCog(bot=mock_bot, project_root=str(PROJECT_ROOT))

    print("\n[1/2] Traitement d'un prompt d'identification...")
    content, reasoning, meta = await cog.process_prompt(
        user_message="Qui es-tu et quel est ton rôle ?",
        author_name="Opérateur",
    )
    print("  -> Inférence réussie !")
    print(f"     Palier exécuté : {meta['tier']}")
    print(f"     Fournisseur    : {meta['provider']}")
    print(f"     Modèle actif   : {meta['model']}")
    print(f"     Réponse E-zzio : {content}")

    assert "E-zzio" in content or "ezzio" in content.lower()
    print("\n[2/2] Validation de l'identité : PASS.")


if __name__ == "__main__":
    asyncio.run(main())
