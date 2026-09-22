"""Tests pour core/token_compressor.py.

Module 100% pur : aucune I/O, aucune dépendance externe.
Toutes les fonctions sont testables directement.
"""
from __future__ import annotations

import pytest

from core import token_compressor

# ============================================================
# 1. estimate_tokens
# ============================================================

class TestEstimateTokens:
    def test_returns_int(self):
        assert isinstance(token_compressor.estimate_tokens("hello"), int)

    def test_minimum_one(self):
        """Texte vide -> 1 (pas 0)."""
        assert token_compressor.estimate_tokens("") == 1
        assert token_compressor.estimate_tokens(None) == 1

    def test_approximation(self):
        """8 chars -> 2 tokens (len/4)."""
        assert token_compressor.estimate_tokens("abcdefgh") == 2
        # 100 chars -> 25
        assert token_compressor.estimate_tokens("x" * 100) == 25

    def test_handles_non_str(self):
        """Non-str converti en str."""
        assert isinstance(token_compressor.estimate_tokens(12345), int)


# ============================================================
# 2. normalize_ws
# ============================================================

class TestNormalizeWs:
    def test_simple(self):
        assert token_compressor.normalize_ws("hello world") == "hello world"

    def test_collapses_spaces(self):
        assert token_compressor.normalize_ws("a    b\t\tc") == "a b c"

    def test_strips(self):
        assert token_compressor.normalize_ws("  x  ") == "x"

    def test_empty(self):
        assert token_compressor.normalize_ws("") == ""
        assert token_compressor.normalize_ws(None) == ""

    def test_newlines_collapsed(self):
        """Newlines et tabs deviennent des espaces simples."""
        result = token_compressor.normalize_ws("a\n\n\nb")
        assert result == "a b"


# ============================================================
# 3. strip_noise
# ============================================================

class TestStripNoise:
    def test_simple(self):
        assert token_compressor.strip_noise("hello") == "hello"

    def test_reduces_newlines(self):
        """3+ newlines -> 2 max."""
        result = token_compressor.strip_noise("a\n\n\n\n\nb")
        assert result == "a\n\nb"

    def test_keeps_double_newline(self):
        """2 newlines restent 2 newlines."""
        result = token_compressor.strip_noise("a\n\nb")
        assert result == "a\n\nb"

    def test_collapses_tabs(self):
        """2+ espaces/tabs -> 1 espace."""
        result = token_compressor.strip_noise("a  b\t\tc")
        assert result == "a b c"

    def test_empty(self):
        assert token_compressor.strip_noise("") == ""
        assert token_compressor.strip_noise(None) == ""


# ============================================================
# 4. split_sentences
# ============================================================

class TestSplitSentences:
    def test_simple_split(self):
        text = "Ceci est une phrase longue et utile. Voici une autre phrase longue aussi."
        sents = token_compressor.split_sentences(text)
        assert len(sents) >= 2

    def test_filters_short_sentences(self):
        """Phrases < 20 chars filtrées."""
        text = "Court. Ceci est une phrase beaucoup plus longue et utile."
        sents = token_compressor.split_sentences(text)
        # "Court." fait < 20 chars -> filtré
        for s in sents:
            assert len(s) > 20

    def test_empty(self):
        assert token_compressor.split_sentences("") == []
        assert token_compressor.split_sentences(None) == []

    def test_splits_on_question_mark(self):
        text = "Quelle est la question longue et complexe ? Une réponse tout aussi longue ici."
        sents = token_compressor.split_sentences(text)
        assert len(sents) >= 2

    def test_splits_on_exclamation(self):
        text = "Attention ceci est important ! Voici une autre phrase assez longue."
        sents = token_compressor.split_sentences(text)
        assert len(sents) >= 2


# ============================================================
# 5. keywords
# ============================================================

class TestKeywords:
    def test_returns_list(self):
        result = token_compressor.keywords("test test test")
        assert isinstance(result, list)

    def test_filters_stopwords(self):
        """Les mots vides FR/EN ne sont pas retournés."""
        text = "les des une dans pour avec the and for with"
        result = token_compressor.keywords(text)
        for w in result:
            assert w not in {"les", "des", "the", "and", "for", "with"}

    def test_respects_limit(self):
        text = "alpha beta gamma delta epsilon zeta eta theta iota kappa"
        result = token_compressor.keywords(text, limit=3)
        assert len(result) <= 3

    def test_orders_by_frequency(self):
        """Mots plus fréquents d'abord."""
        text = "alpha alpha alpha beta beta gamma"
        result = token_compressor.keywords(text)
        assert result[0] == "alpha"

    def test_filters_short_words(self):
        """Mots < 3 chars filtrés."""
        text = "a ab abc abcd abcde"
        result = token_compressor.keywords(text)
        for w in result:
            assert len(w) >= 3

    def test_empty(self):
        assert token_compressor.keywords("") == []


# ============================================================
# 6. score_sentence
# ============================================================

class TestScoreSentence:
    def test_zero_for_neutral(self):
        """Phrase neutre sans mot-clé -> 0."""
        score = token_compressor.score_sentence("bonjour le monde", set())
        assert score == 0

    def test_keyword_match(self):
        """Chaque mot-clé présent ajoute 1."""
        score = token_compressor.score_sentence("python est génial", {"python"})
        assert score >= 1

    def test_digit_bonus(self):
        """Présence de chiffre -> +1."""
        score_no_digit = token_compressor.score_sentence("aucun chiffre", set())
        score_digit = token_compressor.score_sentence("42 réponses", set())
        assert score_digit > score_no_digit

    def test_url_error_bonus(self):
        """http/api/error/warning -> +2."""
        score = token_compressor.score_sentence("http request failed", set())
        # 'http' match -> +2
        assert score >= 2

    def test_error_keyword(self):
        score = token_compressor.score_sentence("une error est survenue", set())
        assert score >= 2

    def test_combination(self):
        """Mot-clé + chiffre + error -> score élevé."""
        score = token_compressor.score_sentence(
            "error 404 sur https://api.example.com",
            {"error"},
        )
        # 'error' (déjà dans la phrase) + digit + http -> au moins 3
        assert score >= 3


# ============================================================
# 7. compress_text
# ============================================================

class TestCompressText:
    def test_short_text_unchanged(self):
        """Texte <= max_chars -> mode 'none', ratio 1.0."""
        short = "Ceci est un texte court."
        result = token_compressor.compress_text(short, max_chars=1000)
        assert result["mode"] == "none"
        assert result["ratio"] == 1.0
        assert result["compressed"] == short

    def test_returns_dict_structure(self):
        """Structure du dict retourné."""
        result = token_compressor.compress_text("texte court", max_chars=1000)
        for key in [
            "compressed",
            "original_chars",
            "compressed_chars",
            "estimated_tokens_before",
            "estimated_tokens_after",
            "ratio",
            "mode",
        ]:
            assert key in result, f"clé manquante : {key}"

    def test_hard_mode(self):
        """Mode 'hard' coupe à max_chars."""
        long_text = "x" * 10000
        result = token_compressor.compress_text(long_text, max_chars=100, mode="hard")
        assert result["compressed_chars"] <= 100
        assert result["ratio"] < 1.0

    def test_extractive_mode_selects_sentences(self):
        """Mode extractif sélectionne des phrases."""
        long_text = " ".join([
            f"Phrase numéro {i} qui est suffisamment longue pour être retenue."
            for i in range(50)
        ])
        result = token_compressor.compress_text(long_text, max_chars=200)
        assert len(result["compressed"]) <= 200
        # Mode extractif (pas 'hard' ni 'none')
        assert result["mode"] not in ("hard", "none")

    def test_empty_text(self):
        """Texte vide -> mode 'none'."""
        result = token_compressor.compress_text("")
        assert result["mode"] == "none"

    def test_original_chars_correct(self):
        """original_chars reflète la longueur réelle."""
        text = "abc" * 100
        result = token_compressor.compress_text(text, max_chars=10, mode="hard")
        assert result["original_chars"] == len(text)
