"""
E-ZZIO Sovereign Generator — PDF Document Engine.
Génère des documents PDF professionnels et paginés via ReportLab Platypus.
"""
from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch

logger = logging.getLogger("PdfEngine")


class PdfEngine:
    """Moteur souverain de génération de documents PDF."""

    def __init__(self, workspace_root: str = "G:\\AI\\E-zzio"):
        self.workspace_root = Path(workspace_root).resolve()
        self.exports_dir = self.workspace_root / "outputs"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def generate_pdf(
        self,
        filename: str,
        title: str,
        sections: List[Dict[str, Any]],
        author: str = "E-ZZIO Autonomous Core"
    ) -> Dict[str, Any]:
        """
        Génère un document PDF paginé avec titres, textes, puces et tableaux.
        sections: [
            {"type": "heading", "level": 1, "text": "1. Synthèse Opérationnelle"},
            {"type": "paragraph", "text": "Contenu du document..."},
            {"type": "bullet", "items": ["Item A", "Item B"]},
            {"type": "table", "headers": ["Col A", "Col B"], "rows": [["1", "2"]]}
        ]
        """
        clean_name = os.path.basename(filename.strip())
        if not clean_name.endswith(".pdf"):
            clean_name += ".pdf"

        out_path = self.exports_dir / clean_name

        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=A4,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        styles = getSampleStyleSheet()
        
        # Styles personnalisés
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0EA5E9'),
            alignment=1,  # Centré
            spaceAfter=6
        )

        sub_style = ParagraphStyle(
            'DocSub',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748B'),
            alignment=1,
            spaceAfter=15
        )

        h1_style = ParagraphStyle(
            'Heading1_Custom',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#0F172A'),
            spaceBefore=14,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            'Body_Custom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155'),
            spaceAfter=8
        )

        bullet_style = ParagraphStyle(
            'Bullet_Custom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#334155'),
            leftIndent=15,
            spaceAfter=4
        )

        story = []

        # En-tête
        story.append(Paragraph(title, title_style))
        story.append(Paragraph(f"Document officiel généré souverainement par {author}", sub_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0'), spaceAfter=14))

        # Éléments de contenu
        for sec in sections:
            s_type = sec.get("type", "paragraph")

            if s_type == "heading":
                story.append(Paragraph(sec.get("text", ""), h1_style))

            elif s_type == "paragraph":
                story.append(Paragraph(sec.get("text", ""), body_style))

            elif s_type == "bullet":
                for itm in sec.get("items", []):
                    story.append(Paragraph(f"• &nbsp; {itm}", bullet_style))
                story.append(Spacer(1, 4))

            elif s_type == "table":
                headers = sec.get("headers", [])
                rows = sec.get("rows", [])
                table_data = []
                if headers:
                    table_data.append([Paragraph(f"<b>{h}</b>", body_style) for h in headers])
                for r in rows:
                    table_data.append([Paragraph(str(cell), body_style) for cell in r])

                if table_data:
                    t = Table(table_data, colWidths=None)
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0 if headers else -1), colors.HexColor('#1E293B')),
                        ('TEXTCOLOR', (0, 0), (-1, 0 if headers else -1), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                        ('TOPPADDING', (0, 0), (-1, -1), 6),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                    ]))
                    story.append(Spacer(1, 6))
                    story.append(t)
                    story.append(Spacer(1, 8))

        doc.build(story)
        logger.info("[PDF-ENGINE] Document PDF généré avec succès : %s", out_path)

        return {
            "ok": True,
            "filename": clean_name,
            "path": str(out_path),
            "size_bytes": out_path.stat().st_size
        }
