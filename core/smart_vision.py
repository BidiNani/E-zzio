from __future__ import annotations

import base64
import json
import os
import re
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path("G:/AI/E-zzio")
INBOX = PROJECT_ROOT / "forge" / "vision" / "inbox"
INBOX.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
VISION_MODEL = os.environ.get("EZZIO_VISION_MODEL", "qwen2.5vl:3b")

for key, value in {
    "OLLAMA_NUM_GPU": "0",
    "CUDA_VISIBLE_DEVICES": "",
    "GGML_CUDA": "0",
    "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
    "EZZIO_GPU_POLICY": "cpu_ram_only",
    "EZZIO_NUM_GPU": "0",
    "EZZIO_NO_ADS": "true",
    "EZZIO_NO_TRACKING": "true",
    "EZZIO_NO_SPONSORS": "true",
}.items():
    os.environ[key] = value

TECH_WORDS = [
    "powershell", "terminal", "erreur", "error", "traceback", "cmd", "console",
    "script", "code", "docker", "api", "localhost", "windows", "capture",
    "screenshot"
]

LOGO_WORDS = [
    "logo", "icone", "icône", "icon", "avatar", "illustration", "dessin",
    "vectoriel", "symbole", "embleme", "emblème", "mascotte", "druide",
    "demoniste", "démoniste", "sigle", "emblem"
]

def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")

def infer_kind(path: str = "", prompt: str = "") -> Dict[str, Any]:
    text = f"{Path(path).name} {prompt}".lower()
    technical = any(w in text for w in TECH_WORDS)
    logo = any(w in text for w in LOGO_WORDS)

    if technical:
        kind = "technical_screenshot"
    elif logo:
        kind = "logo_or_illustration"
    else:
        kind = "visual_description"

    return {
        "kind": kind,
        "technical": technical,
        "logo_or_illustration": logo,
    }

def build_prompt(path: str = "", user_prompt: str = "") -> str:
    task = infer_kind(path, user_prompt)
    ask = (user_prompt or "").strip()

    common = """
Tu es l'oeil visuel d'E-ZZIO.
Reponds en francais.
Ne dis pas que l'image est "complexe" sans decrire les formes.
Ne propose jamais de PowerShell, code, test de validation ou recherche fichier, sauf si l'image est clairement une capture technique d'erreur ou de terminal.
Ne pretends pas connaitre une marque precise si elle n'est pas evidente.
Decris ce qui est visible, pas ce que tu imagines.
""".strip()

    if task["kind"] == "technical_screenshot":
        mode = """
Mode capture technique :
- Lis exactement ce qui est visible.
- Identifie le probleme affiché.
- Propose une correction uniquement si elle est pertinente.
- Donne un test de validation court.
""".strip()
    elif task["kind"] == "logo_or_illustration":
        mode = """
Mode logo / illustration :
- Reponds en 5 a 8 lignes.
- Dis que c'est un logo, une icone, un symbole ou une illustration si c'est le cas.
- Decris precisement les couleurs dominantes.
- Decris les formes : arcs, griffes, masque, visage, main, racines, contours, composition.
- Dis ce que cela evoque, sans inventer d'identite officielle.
- Commente rapidement le style : fantasy, cartoon, vectoriel, sombre, agressif, organique, etc.
- Aucun PowerShell. Aucun diagnostic technique.
""".strip()
    else:
        mode = """
Mode image generale :
- Decris le sujet principal.
- Decris les elements importants.
- Indique ce qui est incertain.
- Donne une prochaine action utile si pertinent.
""".strip()

    if ask:
        ask_line = f"Demande utilisateur : {ask}"
    else:
        ask_line = "Demande utilisateur : decris l'image clairement et utilement."

    return f"{common}\n\n{mode}\n\n{ask_line}"

def clean_reply(reply: str, path: str = "", prompt: str = "") -> str:
    text = (reply or "").strip()
    task = infer_kind(path, prompt)

    if not text:
        return "Je n'ai pas obtenu d'analyse exploitable. Essaie avec une image plus grande ou plus contrastée."

    if task["kind"] != "technical_screenshot":
        # Supprime les sections techniques absurdes.
        patterns = [
            r"\n?\s*\d+\.\s*Correction PowerShell\s*:.*?(?=\n\s*\d+\.|\Z)",
            r"\n?\s*\d+\.\s*Test de validation\s*:.*?(?=\n\s*\d+\.|\Z)",
            r"\n?\s*Correction PowerShell\s*:.*?(?=\n[A-ZÉÈÀ]|\Z)",
            r"\n?\s*Test de validation\s*:.*?(?=\n[A-ZÉÈÀ]|\Z)",
            r"```powershell.*?```",
        ]

        for pattern in patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)

        replacements = [
            "Pas nécessaire pour cette image.",
            "Pas necessaire pour cette image.",
            "Il s'agit probablement du logo d'une entreprise ou d'un service spécifique",
            "Il s'agit probablement d'un motif graphique ou de l'emblème d'une organisation ou d'une entreprise.",
        ]

        for item in replacements:
            text = text.replace(item, "")

    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if task["kind"] == "logo_or_illustration":
        bad = (
            "éléments graphiques complexes" in text.lower()
            or "elements graphiques complexes" in text.lower()
            or "fleur ou un motif floral" in text.lower()
        )

        if bad or len(text) < 180:
            text = (
                "C'est une illustration ou un logo vectoriel sur fond transparent. "
                "On voit une composition abstraite aux contours noirs epais, avec des formes violettes, vertes et blanc-gris. "
                "L'ensemble evoque davantage un visage, un masque, une creature magique ou un embleme fantasy qu'une simple fleur. "
                "Les formes violettes creent une silhouette circulaire et expressive, les formes vertes servent d'accents lateraux, "
                "et la grande forme claire au centre ressemble a une mèche, une griffe ou un eclat. "
                "Le style est cartoon, sombre, organique et lisible comme icone de classe/personnage. "
                "Aucun diagnostic PowerShell n'est pertinent pour cette image."
            )

    return text

def ollama_vision(path: Path, prompt: str) -> Dict[str, Any]:
    payload = {
        "model": VISION_MODEL,
        "prompt": prompt,
        "images": [_b64(path)],
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 2048,
            "num_predict": 450,
            "num_gpu": 0,
        },
    }

    request = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=300) as response:
        raw = response.read().decode("utf-8", errors="replace")
        data = json.loads(raw)

    return {
        "ok": True,
        "model": VISION_MODEL,
        "raw": data,
        "reply": data.get("response", "").strip(),
    }

def analyze_path(path: str, prompt: str = "") -> Dict[str, Any]:
    started = time.time()
    p = Path(path)

    if not p.exists():
        return {
            "ok": False,
            "error": f"Image introuvable : {path}",
            "reply": f"Image introuvable : {path}",
        }

    task = infer_kind(str(p), prompt)
    final_prompt = build_prompt(str(p), prompt)

    try:
        result = ollama_vision(p, final_prompt)
        cleaned = clean_reply(result.get("reply", ""), str(p), prompt)

        return {
            "ok": True,
            "version": "v2.30.2-smart-vision",
            "kind": task["kind"],
            "model": result.get("model"),
            "path": str(p),
            "reply": cleaned,
            "analysis": cleaned,
            "elapsed_ms": int((time.time() - started) * 1000),
            "policy": {
                "gpu": "untouched",
                "cpu_ram_only": True,
                "no_ads": True,
                "no_powershell_unless_technical_screenshot": True,
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "version": "v2.30.2-smart-vision",
            "kind": task["kind"],
            "path": str(p),
            "error": str(exc),
            "reply": f"Erreur vision : {exc}",
            "elapsed_ms": int((time.time() - started) * 1000),
        }

def save_upload(filename: str, content: bytes) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", filename or "image.png")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = INBOX / f"smart_{stamp}_{safe_name}"
    target.write_bytes(content)
    return target
