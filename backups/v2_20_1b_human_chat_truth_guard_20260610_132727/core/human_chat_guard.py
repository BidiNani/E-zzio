from __future__ import annotations

import re
from typing import Any, Dict, Optional

def normalize(text: str) -> str:
    return (text or "").strip().lower()

def wants_system_state(text: str) -> bool:
    low = normalize(text)
    return (
        ("état" in low or "etat" in low or "status" in low or "brief" in low)
        and ("système" in low or "systeme" in low or "pc" in low or "e-zzio" in low or "ezzio" in low)
    )

def wants_next_optimization(text: str) -> bool:
    low = normalize(text)
    return (
        ("optimisation" in low or "optimiser" in low or "amélioration" in low or "amelioration" in low)
        and ("sans rien casser" in low or "prochaine" in low or "pc" in low or "e-zzio" in low or "ezzio" in low)
    )

def system_state_reply() -> str:
    return (
        "État rapide E-ZZIO : système PC propre et prêt, maintenance OK, human loop actif, "
        "cerveau routeur disponible, CPU/RAM only, GPU intact, zéro pub, zéro tracking."
    )

def next_optimization_reply() -> str:
    return (
        "Je peux préparer la prochaine optimisation PC sans rien casser : d'abord audit, puis plan, "
        "backup, test, validation endpoint, rapport JSON, et seulement ensuite une modification explicite si tu confirmes."
    )

def deterministic_human_reply(text: str) -> Optional[Dict[str, Any]]:
    if wants_system_state(text):
        return {
            "reply": system_state_reply(),
            "command": "/state",
            "deterministic": True,
        }

    if wants_next_optimization(text):
        return {
            "reply": next_optimization_reply(),
            "command": "/prepare-optimization",
            "deterministic": True,
        }

    return None

def sanitize_human_chat_reply(reply: str) -> str:
    text = reply or ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("\x00", "").strip()

    text = text.replace("E-ZZZIO", "E-ZZIO")
    text = text.replace("EZZZIO", "EZZIO")
    text = text.replace("E-ZZIOO", "E-ZZIO")

    risky_replacements = [
        (
            "je vais effectuer",
            "je peux préparer un plan pour effectuer, après ta confirmation,"
        ),
        (
            "je vais analyser",
            "je peux analyser si tu me le demandes explicitement"
        ),
        (
            "je vais supprimer",
            "je ne supprimerai rien sans confirmation explicite ; je peux seulement préparer une proposition de suppression"
        ),
        (
            "je vais fermer",
            "je ne fermerai rien sans confirmation explicite ; je peux seulement proposer quoi fermer"
        ),
        (
            "je m'occuperai de",
            "je peux t'aider à préparer"
        ),
        (
            "je me concentrerai sur le nettoyage",
            "je peux préparer un nettoyage en dry-run, sans appliquer de changement"
        ),
        (
            "supprimant les fichiers temporaires",
            "en listant d'abord les fichiers temporaires candidats en quarantaine/dry-run"
        ),
    ]

    low = text.lower()
    for old, new in risky_replacements:
        if old in low:
            text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
            low = text.lower()

    risky_internet = [
        "sans nécessiter de connexion internet",
        "ne nécessite pas de connexion internet",
        "conçu pour fonctionner sans connexion internet",
        "fonctionner sans connexion internet",
    ]

    if any(x in low for x in risky_internet):
        text = (
            "Le cœur PC d'E-ZZIO fonctionne localement en CPU/RAM only, sans pub ni tracking. "
            "Les connecteurs externes comme Discord, Messenger ou certaines API publiques nécessitent Internet seulement s'ils sont configurés."
        )

    # Ne pas laisser une réponse libre annoncer une action réelle.
    action_words = [
        "j'effectuerai",
        "je supprimerai",
        "je fermerai",
        "je modifierai",
        "je lancerai le nettoyage",
    ]

    if any(word in text.lower() for word in action_words):
        text = (
            "Je peux préparer un plan sûr, avec backup, logs, validation et rollback. "
            "Je n'exécuterai aucune action destructive ou système sans confirmation explicite."
        )

    return text.strip()
