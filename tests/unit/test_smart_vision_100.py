"""Test cible : smart_vision.clean_reply branche 182->193.

Branche : task.kind == "logo_or_illustration" ET bad == False ET len(text) >= 180.
Resultat : le texte est retourne inchange (pas de fallback).
"""
from __future__ import annotations

from core.smart_vision import clean_reply


class TestCleanReplyLogoLongCleanText:
    """L182->193 : la branche FALSE du if bad or len<180."""

    def test_logo_long_clean_text_returned_unchanged(self):
        """Texte long (>180), pas de marqueurs 'bad' -> inchange."""
        # Texte propre, >180 chars, sans les patterns rejetes
        clean_text = (
            "Ceci est un logo illustrant une creature fantastique. "
            "Il presente des contours nets avec une dominante violette "
            "et des accents verts sur un fond sombre, ce qui evoque "
            "un univers fantasy distinctif et memorable pour ce projet."
        )
        assert len(clean_text) >= 180, "le texte doit depasser 180 chars"

        result = clean_reply(clean_text, path="logo_test.png", prompt="")

        # Branche 182->193 : pas de remplacement par le fallback
        assert result == clean_text.strip()
        assert "illustration ou un logo vectoriel sur fond transparent" not in result

    def test_logo_short_text_triggers_fallback(self):
        """Non-regression : texte court (<180) -> fallback applique."""
        short_text = "Un petit logo."
        result = clean_reply(short_text, path="logo.png", prompt="")

        # La branche TRUE applique le fallback
        assert "illustration ou un logo vectoriel" in result

    def test_logo_bad_pattern_triggers_fallback(self):
        """Non-regression : pattern 'bad' present -> fallback applique."""
        bad_text = (
            "Voici un logo avec des elements graphiques complexes "
            "qui meritent une analyse approfondie et detaillee afin "
            "de bien comprendre toutes les subtilites visuelles de "
            "cette oeuvre singuliere et ses nombreuses variations."
        )
        assert len(bad_text) >= 180, "texte long pour prouver que c'est 'bad' qui declenche"
        result = clean_reply(bad_text, path="logo.png", prompt="")

        # 'elements graphiques complexes' -> bad True -> fallback
        assert "illustration ou un logo vectoriel" in result

    def test_non_logo_kind_skips_logo_block(self):
        """Non-regression : kind != logo -> bloc 175-191 non execute."""
        text = "Voici une capture d'ecran d'un terminal PowerShell."
        result = clean_reply(text, path="screenshot_error.png", prompt="")
        # Le bloc logo ne s'applique pas -> texte non remplace par fallback logo
        assert "illustration ou un logo vectoriel sur fond transparent" not in result
