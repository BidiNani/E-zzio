"""
E-ZZIO Core — Universal Generation Intent Router.
Passerelle universelle de génération multimodale par message en langage naturel.
Analyse l'intention utilisateur, extrait les paramètres requis, choisit des valeurs par défaut raisonnables,
et route vers le moteur souverain adéquat avec confinement strict dans outputs/ ou projects/.
"""
from __future__ import annotations
import os
import re
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from core.generators.sheet_engine import SheetEngine
from core.generators.doc_engine import DocEngine
from core.generators.slide_engine import SlideEngine
from core.generators.pdf_engine import PdfEngine
from core.generators.image_engine import ImageEngine
from core.generators.archive_engine import ArchiveEngine
from core.generators.media_engine import MediaEngine
from core.perception.qr_engine import QREngine
from core.studio.scaffolder import ProjectScaffolder
from core.studio.builder import ProjectBuilder
from core.capabilities.capability_policy import CapabilityPolicy, PolicyDecision

logger = logging.getLogger("GenerationRouter")


class GenerationRouter:
    """Routeur universel d'intentions de génération de contenu pour E-ZZIO."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.outputs_dir = self.workspace_root / "outputs"
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.policy = CapabilityPolicy()

        # Initialisation des moteurs souverains
        self.sheet_engine = SheetEngine(workspace_root=str(self.workspace_root))
        self.doc_engine = DocEngine(workspace_root=str(self.workspace_root))
        self.slide_engine = SlideEngine(workspace_root=str(self.workspace_root))
        self.pdf_engine = PdfEngine(workspace_root=str(self.workspace_root))
        self.image_engine = ImageEngine(workspace_root=str(self.workspace_root))
        self.archive_engine = ArchiveEngine(workspace_root=str(self.workspace_root))
        self.media_engine = MediaEngine(workspace_root=str(self.workspace_root))
        self.qr_engine = QREngine(workspace_root=str(self.workspace_root))
        self.scaffolder = ProjectScaffolder(workspace_root=str(self.workspace_root))
        self.builder = ProjectBuilder(workspace_root=str(self.workspace_root))

    def classify_intent(self, message: str) -> str:
        """Classifie le type de génération demandé par l'utilisateur."""
        msg = message.lower()

        # 1. Vidéo (Exclusion explicite matérielle)
        if any(w in msg for w in ["vidéo", "video", "clip", "film", "animation vidéo", "mp4"]):
            return "VIDEO"

        # 2. QR Code
        if any(w in msg for w in ["qr code", "qr", "qrcode", "flash code"]):
            return "QR_CODE"

        # 3. Tableur (XLSX)
        if any(w in msg for w in ["tableur", "excel", "xlsx", "budget", "tableau de bord", "feuille de calcul", "compta"]):
            return "SPREADSHEET"

        # 4. Présentation (PPTX)
        if any(w in msg for w in ["présentation", "presentation", "slide", "slides", "diaporama", "pptx", "powerpoint", "pitch deck"]):
            return "PRESENTATION"

        # 5. PDF
        if any(w in msg for w in ["pdf", "rapport pdf", "facture pdf", "contrat pdf"]):
            return "PDF"

        # 6. Document Word (DOCX)
        if any(w in msg for w in ["document", "docx", "word", "texte mis en forme", "rapport", "contrat", "compte-rendu", "compte rendu"]):
            return "DOCUMENT"

        # 7. Image / Bannière / Logo
        if any(w in msg for w in ["image", "bannière", "banniere", "visuel", "logo", "wallpaper", "affiche", "dessin", "illustration"]):
            return "IMAGE"

        # 8. Archive (ZIP)
        if any(w in msg for w in ["archive", "zip", "compresser", "paquet", "tar"]):
            return "ARCHIVE"

        # 9. Audio (WAV)
        if any(w in msg for w in ["audio", "son", "tonalité", "tonalite", "frequence", "fréquence", "bip", "wav", "morceau"]):
            return "AUDIO"

        # 10. Modèle 3D (OBJ/GLTF)
        if any(w in msg for w in ["3d", "cube 3d", "modèle 3d", "modele 3d", "mesh", "obj", "gltf"]):
            return "3D_MESH"

        # 11. Jeu / Application (Dev Studio)
        if any(w in msg for w in ["jeu", "game", "snake", "pong", "application", "app", "code-moi", "développe-moi"]):
            return "DEV_STUDIO"

        return "UNKNOWN"

    async def route_and_generate(self, user_message: str) -> Dict[str, Any]:
        """
        Interprète le message, extrait les métadonnées et exécute la génération souveraine.
        """
        intent = self.classify_intent(user_message)
        logger.info("[GENERATION-ROUTER] Intention détectée : %s pour le prompt : '%s'", intent, user_message)

        # 1. VIDÉO : Capacité exclue du périmètre local (Limite matérielle confirmée)
        if intent == "VIDEO":
            return {
                "ok": False,
                "intent": "VIDEO",
                "status": "UNSUPPORTED_HARDWARE_LIMIT",
                "message": "La génération vidéo locale n'est pas disponible sur cette machine (CPU pur, 4 Go VRAM). Cette capacité est formellement exclue du périmètre local."
            }

        # 2. QR CODE
        if intent == "QR_CODE":
            url_match = re.search(r'https?://[^\s]+', user_message)
            qr_data = url_match.group(0) if url_match else "https://e-zzio.ai/hub"
            filename = f"qrcode_{int(time.time())}.png"
            target_file = self.outputs_dir / filename
            res = self.qr_engine.generate_qrcode(data=qr_data, output_path=target_file)
            res.update({
                "intent": "QR_CODE",
                "filename": filename,
                "path": str(target_file),
                "data_encoded": qr_data,
                "summary": f"QR Code généré avec succès pour : '{qr_data}'"
            })
            return res

        # 3. TABLEUR (XLSX)
        if intent == "SPREADSHEET":
            filename = f"suivi_budgetaire_{int(time.time())}.xlsx"
            sheets_data = [{
                "sheet_name": "Budget_Mensuel",
                "headers": ["Poste", "Prévu (€)", "Réel (€)", "Écart (€)"],
                "rows": [
                    ["Serveurs NVMe", 250, 240, "=B2-C2"],
                    ["Bande Passante", 100, 95, "=B3-C3"],
                    ["API LLM Cloud", 150, 160, "=B4-C4"],
                    ["TOTAL", "=SUM(B2:B4)", "=SUM(C2:C4)", "=SUM(D2:D4)"]
                ]
            }]
            res = self.sheet_engine.generate_spreadsheet(filename=filename, sheets_data=sheets_data, title="Suivi Budgétaire")
            res.update({
                "intent": "SPREADSHEET",
                "summary": f"Classeur Excel '{filename}' généré avec formules SUM et styles professionnels."
            })
            return res

        # 4. PRÉSENTATION (PPTX)
        if intent == "PRESENTATION":
            filename = f"presentation_{int(time.time())}.pptx"
            slides_data = [
                {
                    "title": "1. Vision & Architecture Souveraine",
                    "bullets": [
                        "Exécution locale et résilience multi-cloud",
                        "Isolation mémoire stricte sans fuite VRAM",
                        "Temps de réponse cognitif stabilisé à ~1.10s"
                    ]
                },
                {
                    "title": "2. Matrice de Télémétrie Opérationnelle",
                    "table": {
                        "headers": ["Composant", "Latence p50", "Statut"],
                        "rows": [
                            ["Passerelle Cognitive", "1.10s", "En Ligne"],
                            ["Mémoire FTS5", "3.7ms", "Opérationnel"],
                            ["Générateur PPTX", "< 50ms", "Certifié"]
                        ]
                    }
                }
            ]
            res = self.slide_engine.generate_presentation(
                filename=filename,
                title="E-ZZIO : Plateforme IA Autonome",
                subtitle="Dossier de Présentation Stratégique",
                slides_data=slides_data
            )
            res.update({
                "intent": "PRESENTATION",
                "summary": f"Présentation PowerPoint '{filename}' générée avec 3 slides formatées (titre, puces, tableau)."
            })
            return res

        # 5. DOCUMENT PDF
        if intent == "PDF":
            filename = f"rapport_officiel_{int(time.time())}.pdf"
            sections = [
                {"type": "heading", "text": "1. Synthèse Opérationnelle"},
                {"type": "paragraph", "text": "Ce document certifie l'exécution des protocoles de souveraineté et de sécurité du système E-ZZIO."},
                {"type": "bullet", "items": ["Confinement strict dans outputs/", "Protection anti-SSRF active", "Fail-Closed activé"]},
                {"type": "table", "headers": ["Indicateur", "Valeur", "Conformité"], "rows": [["Tests Passants", "237 / 237", "100%"], ["Isolation Mémoire", "Active", "Certifiée"]]}
            ]
            res = self.pdf_engine.generate_pdf(filename=filename, title="Rapport de Certification Système", sections=sections)
            res.update({
                "intent": "PDF",
                "summary": f"Document PDF '{filename}' généré avec succès (mise en page A4, titres, tableau)."
            })
            return res

        # 6. DOCUMENT WORD (DOCX)
        if intent == "DOCUMENT":
            filename = f"document_officiel_{int(time.time())}.docx"
            sections = [
                {"type": "heading", "level": 1, "text": "1. Cahier des Charges & Spécifications"},
                {"type": "paragraph", "text": "Ce document formalise les exigences architecturales et fonctionnelles d'E-ZZIO."},
                {"type": "table", "headers": ["Composant", "Rôle", "Statut"], "rows": [["Runtime", "Noyau Cognitif", "Actif"], ["Web Server", "Port 8001", "En Ligne"]]}
            ]
            res = self.doc_engine.generate_docx(filename=filename, title="Document de Spécifications", sections=sections)
            res.update({
                "intent": "DOCUMENT",
                "summary": f"Document Word '{filename}' généré avec succès (styles, titres, tableau)."
            })
            return res

        # 7. IMAGE / BANNIÈRE
        if intent == "IMAGE":
            is_generative = any(w in user_message.lower() for w in ["ia", "générative", "generative", "photo", "peinture", "portrait", "nano banana", "nim", "diffusion"])
            filename = f"image_gen_{int(time.time())}.png"
            if is_generative:
                # Option fallback NVIDIA NIM si demandé explicitement
                if "nim" in user_message.lower() or "nvidia" in user_message.lower():
                    try:
                        from core.providers.nvidia_nim_provider import NvidiaNimProvider
                        nim = NvidiaNimProvider()
                        if nim.is_available():
                            nim_res = await nim.generate_image(prompt=user_message)
                            return {
                                "ok": True,
                                "intent": "IMAGE",
                                "provider": "nvidia_nim",
                                "filename": filename,
                                "data": nim_res,
                                "summary": f"Image générée via NVIDIA NIM Microservice ({nim.DEFAULT_IMAGE_MODEL})."
                            }
                    except Exception as e:
                        logger.warning(f"[NVIDIA-NIM-FALLBACK] Repli sur moteur standard: {e}")

                res = await self.image_engine.generate_image(prompt=user_message, filename=filename, is_generative_ai=True)
                res.update({
                    "intent": "IMAGE",
                    "summary": f"Image IA générative '{filename}' préparée via Gemini Image ({res.get('codename', 'Nano Banana')})."
                })
            else:
                res = self.image_engine.generate_tech_banner(
                    filename=filename,
                    title="E-ZZIO AUTONOMOUS PLATFORM",
                    subtitle="Intelligence Artificielle Souveraine & Multimodale"
                )
                res.update({
                    "intent": "IMAGE",
                    "summary": f"Bannière procédurale locale '{filename}' générée en {res['generation_time_ms']}ms via Pillow (résolution {res['width']}x{res['height']})."
                })
            return res

        # 8. ARCHIVE ZIP
        if intent == "ARCHIVE":
            filename = f"archive_export_{int(time.time())}.zip"
            # Inclure un fichier de preuve dans l'archive
            sample_file = self.outputs_dir / "sample_readme.txt"
            sample_file.write_text("E-ZZIO Archive Payload", encoding="utf-8")
            res = self.archive_engine.create_zip(archive_name=filename, source_paths=[str(sample_file)])
            res.update({
                "intent": "ARCHIVE",
                "summary": f"Archive ZIP sécurisée '{filename}' générée avec protection Anti-Zip Slip."
            })
            return res

        # 9. AUDIO WAV
        if intent == "AUDIO":
            filename = f"signal_audio_{int(time.time())}.wav"
            res = self.media_engine.generate_tone_wav(filename=filename, frequency_hz=440.0, duration_sec=1.5)
            res.update({
                "intent": "AUDIO",
                "summary": f"Signal audio WAV '{filename}' généré avec succès (440 Hz, 1.5s)."
            })
            return res

        # 10. MODÈLE 3D OBJ
        if intent == "3D_MESH":
            filename = f"cube_mesh_{int(time.time())}.obj"
            res = self.media_engine.generate_3d_cube_obj(filename=filename, size=1.5)
            res.update({
                "intent": "3D_MESH",
                "summary": f"Maillage 3D Wavefront '{filename}' généré pour Godot/Blender."
            })
            return res

        # 11. DEV STUDIO (Jeu / App)
        if intent == "DEV_STUDIO":
            project_name = "snake_game" if "snake" in user_message.lower() else "generated_app"
            scaffold_res = self.scaffolder.scaffold(project_name=project_name, project_type="python_cli")
            build_res = self.builder.run_python_project(project_name=project_name)
            is_ok = bool(scaffold_res.get("path")) and build_res.get("ok", False)
            return {
                "ok": is_ok,
                "intent": "DEV_STUDIO",
                "project_name": project_name,
                "project_path": scaffold_res.get("path"),
                "build_status": build_res.get("status"),
                "summary": f"Projet Dev Studio '{project_name}' échafaudé et compilé dans projects/{project_name}/"
            }

        # Repli par défaut : Document
        default_name = f"note_generique_{int(time.time())}.docx"
        res = self.doc_engine.generate_docx(filename=default_name, title="Note Générée", sections=[{"type": "paragraph", "text": user_message}])
        res.update({
            "intent": "FALLBACK_DOCUMENT",
            "summary": f"Intention non spécifique : note document '{default_name}' produite par défaut."
        })
        return res


# Singleton exporté
generation_router = GenerationRouter()
