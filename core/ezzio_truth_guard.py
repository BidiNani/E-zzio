from __future__ import annotations

REAL_PC_PROFILE = {
    "cpu": "AMD Ryzen 9 5900X",
    "ram": "32 Go DDR4",
    "gpu": "MSI GTX 1650 4 Go",
    "policy": "CPU/RAM only",
    "gpu_policy": "GPU untouched / réservé gaming",
}

REAL_PC_PROFILE_TEXT = (
    "Configuration vérifiée d'Enrik : AMD Ryzen 9 5900X, 32 Go DDR4, "
    "MSI GTX 1650 4 Go. Politique E-ZZIO : CPU/RAM only, GPU untouched."
)

FORBIDDEN_HARDWARE_CLAIMS = [
    "i7-11700k",
    "intel core i7",
    "rtx 3070",
    "64 gb",
    "64 go",
    "geforce rtx",
]

BAD_REFUSALS = [
    "je n'ai pas été programmée",
    "je n'ai pas ete programmee",
    "cela dépasse mes capacités",
    "cela depasse mes capacites",
    "dépasse ma mission",
    "depasse ma mission",
    "je ne peux pas vous fournir d'informations à ce sujet",
    "je ne peux pas vous fournir d'informations a ce sujet",
]

GAMING_WORDS = [
    "wow",
    "world of warcraft",
    "demoniste",
    "démoniste",
    "chaman",
    "druide",
    "warlock",
    "shaman",
    "logo vectoriel",
    "classe",
    "embleme",
    "emblème",
    "icone",
    "icône",
    "fantasy",
]

def is_hardware_question(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in [
        "config", "configuration", "matériel", "materiel", "cpu", "ram", "gpu",
        "carte graphique", "processeur", "combien de ram", "état rapide", "etat rapide",
        "système", "systeme"
    ])

def is_user_correction(text: str) -> bool:
    t = (text or "").lower().strip()
    return (
        t.startswith("c'est ")
        or t.startswith("ce n'est pas")
        or " en fait " in t
        or "tu te trompes" in t
        or "pas terrible" in t
        or "depuis quand" in t
    )

def is_gaming_context(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in GAMING_WORDS)

def correction_ack(text: str) -> str:
    t = text or ""

    if "64" in t.lower() or "ram" in t.lower() or "rtx" in t.lower() or "i7" in t.lower():
        return (
            "Tu as raison : je ne dois pas inventer ta configuration matérielle.\n\n"
            f"{REAL_PC_PROFILE_TEXT}\n\n"
            "Toute autre configuration annoncée, comme i7, RTX 3070 ou 64 Go de RAM, est une hallucination et doit être rejetée."
        )

    if is_gaming_context(t):
        return (
            "Tu as raison. Je corrige l'interprétation : si tu indiques que c'est un logo vectoriel lié à World of Warcraft, "
            "je dois utiliser ce contexte au lieu de refuser.\n\n"
            "Interprétation corrigée : c'est un logo / emblème vectoriel de style fantasy lié à WoW. "
            "Si tu précises démoniste, chaman ou druide, je dois analyser les formes, couleurs et symboliques de cette classe, "
            "sans inventer que c'est une entreprise, et sans proposer de PowerShell pour une image."
        )

    return (
        "Tu as raison, je prends ta correction en compte. Je dois m'appuyer sur ton contexte explicite "
        "et ne pas inventer une explication générique."
    )

def sanitize_reply(reply: str, user_text: str = "") -> str:
    text = (reply or "").strip()
    user = user_text or ""

    if not text:
        return "Je n'ai pas obtenu de réponse exploitable."

    low = text.lower()

    if any(bad in low for bad in FORBIDDEN_HARDWARE_CLAIMS):
        if is_hardware_question(user) or "état rapide" in user.lower() or "etat rapide" in user.lower():
            return (
                "État rapide E-ZZIO : système local opérationnel.\n\n"
                f"{REAL_PC_PROFILE_TEXT}\n\n"
                "Je ne dois pas inventer de matériel. Si une donnée n'est pas lue depuis un endpoint fiable, "
                "je dois dire qu'elle n'est pas vérifiée."
            )

    if is_gaming_context(user) and any(refusal in low for refusal in BAD_REFUSALS):
        return (
            "Oui, je peux traiter ce sujet. WoW, les classes, les logos vectoriels, les styles fantasy "
            "et les références visuelles de jeu vidéo sont dans mon périmètre d'analyse.\n\n"
            "Si tu dis que c'est un logo vectoriel du démoniste sur WoW, je dois utiliser ce contexte : "
            "formes agressives, énergie sombre, symbolique occulte/fel, contrastes marqués, silhouette d'emblème de classe. "
            "Je dois seulement préciser si je ne peux pas garantir que c'est officiel plutôt qu'une version fan-made."
        )

    if is_user_correction(user):
        if any(refusal in low for refusal in BAD_REFUSALS) or len(text) < 260:
            return correction_ack(user)

    return text

def system_prompt(intent: str = "chat") -> str:
    return f"""
Tu es E-ZZIO, ami IA local d'Enrik sur PC.

PROFIL MATÉRIEL VERROUILLÉ :
- CPU : {REAL_PC_PROFILE["cpu"]}
- RAM : {REAL_PC_PROFILE["ram"]}
- GPU : {REAL_PC_PROFILE["gpu"]}
- Politique : {REAL_PC_PROFILE["policy"]}, {REAL_PC_PROFILE["gpu_policy"]}

RÈGLES :
- Réponds en français.
- N'invente jamais la configuration matérielle.
- Ne jamais dire i7, RTX 3070 ou 64 Go RAM pour Enrik.
- Si tu n'es pas certain d'une donnée, dis "non vérifié".
- Tu peux parler de jeux vidéo, World of Warcraft, classes, logos, icônes, fantasy, MAO, dev, UI, images.
- Ne refuse pas un sujet normal en disant que ce n'est pas ta mission.
- Si l'utilisateur corrige ton interprétation, accepte la correction et améliore l'analyse.
- Pas de publicité, pas de tracking, pas de sponsor.
- CPU/RAM only, GPU untouched.
- Si action risquée : proposer, demander confirmation, ne pas exécuter seul.

Intention : {intent}
""".strip()
