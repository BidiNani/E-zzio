DESTRUCTIVE_WORDS = [
    "supprimer",
    "delete",
    "effacer",
    "remove",
    "rm ",
    "del ",
    "format",
    "formatage",
    "wipe",
    "kill",
    "stop-process",
    "nettoie tout",
    "reset",
    "réinitialise",
    "reinitialise",
]

SYSTEM_WORDS = ["registre", "system32", "windows", "program files", "services", "admin", "droits", "firewall", "driver", "gpu", "cuda"]

TECH_WORDS = ["powershell", "python", "fastapi", "svelte", "api", "script", "backend", "frontend", "uvicorn", "ollama", "json", "logs"]


def analyze_request(text):
    lowered = str(text).lower()
    risk = "low"
    intent = "general"
    anticipation = []

    if any(word in lowered for word in TECH_WORDS):
        intent = "technical"
        anticipation += [
            "vérifier les chemins avant modification",
            "prévoir backup et rollback",
            "valider par endpoint ou compilation",
        ]

    if any(word in lowered for word in DESTRUCTIVE_WORDS):
        risk = "high"
        intent = "destructive_or_admin"
        anticipation += [
            "ne jamais supprimer sans cible explicite",
            "faire une sauvegarde avant action",
            "préférer sandbox ou dry-run",
        ]

    if any(word in lowered for word in SYSTEM_WORDS):
        risk = "medium" if risk == "low" else risk
        anticipation += [
            "ne pas toucher au GPU",
            "éviter les modifications système globales",
            "privilégier le périmètre G:/AI/E-zzio",
        ]

    if "autonome" in lowered or "anticipe" in lowered or "tactique" in lowered:
        intent = "strategic_autonomy"
        anticipation += [
            "prioriser diagnostic, plan, exécution contrôlée, vérification",
            "séparer réflexion et action",
            "journaliser les décisions",
        ]

    if "erreur" in lowered or "bug" in lowered or "traceback" in lowered or "syntaxerror" in lowered:
        intent = "debug"
        anticipation += [
            "identifier la cause exacte",
            "corriger le minimum nécessaire",
            "tester immédiatement après correction",
        ]

    # Déduplication
    clean = []
    for item in anticipation:
        if item not in clean:
            clean.append(item)

    return {
        "risk": risk,
        "intent": intent,
        "anticipation": clean,
        "needs_backup": risk in ["medium", "high"] or intent in ["technical", "debug", "strategic_autonomy"],
        "needs_confirmation": risk == "high",
        "recommended_mode": "deep" if intent in ["strategic_autonomy"] else "normal",
    }


def tactical_plan(text):
    analysis = analyze_request(text)
    steps = []

    if analysis["needs_backup"]:
        steps.append("Créer ou vérifier une sauvegarde avant modification.")

    if analysis["intent"] in ["technical", "debug"]:
        steps += [
            "Lire l'erreur ou le comportement exact.",
            "Identifier le fichier ou endpoint concerné.",
            "Corriger de façon minimale et propre.",
            "Compiler ou tester.",
            "Consigner le résultat dans les logs.",
        ]

    elif analysis["intent"] == "strategic_autonomy":
        steps += [
            "Évaluer santé API, modèles, mémoire et actions.",
            "Vérifier les goulots : latence modèle, timeout, logs, port.",
            "Optimiser le routage selon les mesures réelles.",
            "Garder les actions dangereuses sous confirmation.",
            "Produire un rapport lisible.",
        ]

    else:
        steps += [
            "Répondre directement.",
            "Proposer une action suivante utile.",
        ]

    return {
        "analysis": analysis,
        "steps": steps,
    }
