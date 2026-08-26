from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

TECH_WORDS = [
    "powershell",
    "terminal",
    "erreur",
    "error",
    "traceback",
    "cmd",
    "console",
    "script",
    "code",
    "docker",
    "api",
    "localhost",
    "windows",
    "capture ecran",
    "capture écran",
    "screenshot",
]

LOGO_WORDS = [
    "logo",
    "icone",
    "icône",
    "icon",
    "avatar",
    "illustration",
    "dessin",
    "vectoriel",
    "symbole",
    "embleme",
    "emblème",
    "mascotte",
]


def infer_image_task(path: str = "", prompt: str = "") -> Dict[str, Any]:
    text = f"{path} {prompt}".lower()
    suffix = Path(path).suffix.lower()
    filename = Path(path).name.lower()

    is_image = suffix in IMAGE_EXTS
    looks_technical = any(w in text for w in TECH_WORDS)
    looks_logo = any(w in text for w in LOGO_WORDS)

    if any(w in filename for w in ["logo", "icon", "icone", "avatar", "vectoriel", "druide", "emblem", "badge"]):
        looks_logo = True

    if looks_technical:
        kind = "technical_screenshot"
    elif looks_logo:
        kind = "logo_or_illustration"
    elif is_image:
        kind = "general_image"
    else:
        kind = "unknown"

    return {
        "kind": kind,
        "is_image": is_image,
        "looks_technical": looks_technical,
        "looks_logo": looks_logo,
    }


def build_vision_prompt(path: str = "", prompt: str = "") -> str:
    task = infer_image_task(path, prompt)
    user_prompt = (prompt or "").strip()

    base_rules = """
Tu es l'oeil d'E-ZZIO. Reponds en francais.
Ne pretends pas reconnaitre une marque, une personne ou un logo precis si ce n'est pas evident.
Ne dis jamais "Correction PowerShell" sauf si l'image est clairement une capture de terminal, script, erreur ou interface technique.
Ne donne pas une reponse vague du type "elements graphiques complexes" sans decrire les formes visibles.
Decris ce que tu vois reellement.
""".strip()

    if task["kind"] == "technical_screenshot":
        mode = """
Mode capture technique :
1. Lecture exacte de l'ecran.
2. Probleme visible.
3. Cause probable.
4. Correction concrete.
5. Test de validation.
""".strip()
    elif task["kind"] == "logo_or_illustration":
        mode = """
Mode logo / illustration :
1. Type d'image : logo, icone, dessin, symbole ou illustration.
2. Description visuelle precise : formes, couleurs, contours, style, composition.
3. Ce que cela evoque, sans inventer d'identite officielle.
4. Qualite graphique : lisibilite, contraste, usage possible.
5. Reponse courte et utile. Pas de PowerShell.
""".strip()
    else:
        mode = """
Mode image generale :
1. Decris clairement le sujet principal.
2. Decris les elements visibles importants.
3. Signale ce qui est incertain.
4. Donne l'action utile suivante si pertinent.
5. Reponse concise.
""".strip()

    extra = f"Demande utilisateur : {user_prompt}" if user_prompt else "Demande utilisateur : analyse l'image de facon claire et utile."

    return f"{base_rules}\n\n{mode}\n\n{extra}"


def clean_vision_reply(reply: str, path: str = "", prompt: str = "") -> str:
    text = (reply or "").strip()
    task = infer_image_task(path, prompt)

    if not text:
        return "Je n'ai pas obtenu d'analyse exploitable. Essaie avec une image plus grande ou plus contrastee."

    if task["kind"] != "technical_screenshot":
        banned = [
            "Correction PowerShell",
            "Test de validation",
            "Pas necessaire pour cette image",
            "Pas nécessaire pour cette image",
            "Diagnostic : Il s'agit probablement du logo d'une entreprise",
        ]

        for item in banned:
            text = text.replace(item, "")

        text = text.replace("3. Correction PowerShell :", "")
        text = text.replace("4. Test de validation :", "")

    if "elements graphiques complexes" in text.lower() or "éléments graphiques complexes" in text.lower():
        if task["kind"] == "logo_or_illustration":
            text += (
                "\n\nLecture attendue : decris les formes exactes, les couleurs, "
                "les contours, le style et ce que l'icone evoque, sans inventer de marque."
            )

    return text.strip()
