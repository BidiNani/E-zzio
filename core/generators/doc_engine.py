"""
E-ZZIO Sovereign Generator — Document Engine (DOCX & PDF).
Génère des documents professionnels formatés Word (.docx) et des synthèses documentaires.
"""
from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

logger = logging.getLogger("DocEngine")


class DocEngine:
    """Moteur souverain de génération documentaire (DOCX, PDF)."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.exports_dir = self.workspace_root / "outputs"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def generate_docx(
        self,
        filename: str,
        title: str,
        sections: List[Dict[str, Any]],
        author: str = "E-ZZIO Autonomous Core"
    ) -> Dict[str, Any]:
        """
        Génère un document Word (.docx) élégant avec titres, paragraphes, listes et tableaux.
        sections: [
            {"type": "heading", "level": 1, "text": "1. Introduction"},
            {"type": "paragraph", "text": "Contenu du paragraphe..."},
            {"type": "bullet", "items": ["Point A", "Point B"]},
            {"type": "table", "headers": ["Col 1", "Col 2"], "rows": [["A", "B"]]}
        ]
        """
        if not DOCX_AVAILABLE:
            return {"ok": False, "error": "python-docx n'est pas disponible dans l'environnement."}

        clean_name = os.path.basename(filename.strip())
        if not clean_name.endswith(".docx"):
            clean_name += ".docx"

        out_path = self.exports_dir / clean_name

        doc = docx.Document()

        # Propriétés de base
        core_props = doc.core_properties
        core_props.title = title
        core_props.author = author

        # Titre Principal
        title_p = doc.add_paragraph()
        title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_p.add_run(title)
        title_run.font.name = "Segoe UI"
        title_run.font.size = Pt(22)
        title_run.font.bold = True
        title_run.font.color.rgb = RGBColor(14, 165, 233)  # Cyan #0EA5E9

        # Sous-titre
        sub_p = doc.add_paragraph()
        sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        sub_run = sub_p.add_run(f"Généré souverainement par {author}")
        sub_run.font.name = "Segoe UI"
        sub_run.font.size = Pt(10)
        sub_run.font.italic = True
        sub_run.font.color.rgb = RGBColor(100, 116, 139)

        doc.add_paragraph().paragraph_format.space_after = Pt(12)

        # Rendu des sections
        for sec in sections:
            s_type = sec.get("type", "paragraph")

            if s_type == "heading":
                level = min(max(int(sec.get("level", 1)), 1), 4)
                h = doc.add_heading(sec.get("text", ""), level=level)
                h.paragraph_format.space_before = Pt(14)
                h.paragraph_format.space_after = Pt(6)

            elif s_type == "paragraph":
                p = doc.add_paragraph(sec.get("text", ""))
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_after = Pt(8)

            elif s_type == "bullet":
                for itm in sec.get("items", []):
                    p = doc.add_paragraph(itm, style='List Bullet')
                    p.paragraph_format.space_after = Pt(3)

            elif s_type == "table":
                headers = sec.get("headers", [])
                rows = sec.get("rows", [])
                if headers or rows:
                    cols_count = max(len(headers), len(rows[0]) if rows else 1)
                    table = doc.add_table(rows=1 if headers else 0, cols=cols_count)
                    table.alignment = WD_TABLE_ALIGNMENT.CENTER

                    if headers:
                        hdr_cells = table.rows[0].cells
                        for i, h_text in enumerate(headers):
                            hdr_cells[i].text = str(h_text)
                            for p in hdr_cells[i].paragraphs:
                                for r in p.runs:
                                    r.font.bold = True
                                    r.font.color.rgb = RGBColor(255, 255, 255)

                    for r_data in rows:
                        row_cells = table.add_row().cells
                        for i, val in enumerate(r_data):
                            if i < len(row_cells):
                                row_cells[i].text = str(val)

                    doc.add_paragraph().paragraph_format.space_after = Pt(8)

        doc.save(str(out_path))
        logger.info("[DOC-ENGINE] Document DOCX généré avec succès : %s", out_path)

        return {
            "ok": True,
            "filename": clean_name,
            "path": str(out_path),
            "size_bytes": out_path.stat().st_size
        }
