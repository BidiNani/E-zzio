"""Wave 3.5 : le grounding lexical ne suffit pas — le CONTENU factuel
(nombres, dates, entités, portée, causalité, temps) doit s'ancrer."""
import time

import pytest

from core.capabilities.truth_engine import (
    build_evidence_context, verify_response, verify_sentence,
)

NOW = 1_757_000_000.0  # ~2026-09
PUB_C0 = 1_709_000_000.0  # 2024-03
PUB_C1 = 1_696_000_000.0  # 2023-10


@pytest.fixture
def ctx():
    return build_evidence_context([
        {"claim_id": "c0",
         "text": "[tavily] Budget France : Le budget atteint 10 millions "
                 "d'euros en France en 2024.",
         "origin": "budget.gouv.fr", "published_at": PUB_C0,
         "state": "KEEP"},
        {"claim_id": "c1",
         "text": "[tavily] Python 3.12 : Python 3.12 est sorti le "
                 "2 octobre 2023.",
         "origin": "python.org", "published_at": PUB_C1, "state": "KEEP"},
    ])


def test_supported_exact(ctx):
    v, _ = verify_sentence(
        "[c0] En France, le budget atteint 10 millions d'euros en 2024.",
        ctx, NOW)
    assert v == "SUPPORTED"


def test_scope_omission_qualifies(ctx):
    v, _ = verify_sentence(
        "[c0] Le budget atteint 10 millions d'euros en 2024.", ctx, NOW)
    assert v == "PARTIALLY_SUPPORTED"  # France passée sous silence


def test_scope_inflation_rejected(ctx):
    v, reasons = verify_sentence(
        "[c0] Dans le monde, le budget atteint 10 millions d'euros.", ctx, NOW)
    assert v == "UNSUPPORTED" and any("portée" in r for r in reasons)


def test_causality_fabrication_rejected(ctx):
    v, reasons = verify_sentence(
        "[c1] La sortie de Python 3.12 provoque une migration massive.",
        ctx, NOW)
    assert v == "UNSUPPORTED" and any("causalité" in r for r in reasons)


def test_temporal_inflation_rejected(ctx):
    v, _ = verify_sentence(
        "[c0] Le budget atteint actuellement 10 millions d'euros en France.",
        ctx, NOW, volatility_days=30.0)
    assert v == "OUT_OF_SCOPE"  # preuves de 2024, pas actuelles


def test_entity_swap_rejected(ctx):
    v, reasons = verify_sentence(
        "[c1] Python 3.11 est sorti le 2 octobre 2023.", ctx, NOW)
    assert v == "UNSUPPORTED"


def test_number_drift_matrix(ctx):
    cases = [
        ("[c0] Le budget atteint 12 millions d'euros en France.", "CONTRADICTED"),
        ("[c0] Le budget atteint 10 millions de dollars en France.", "UNSUPPORTED"),
        ("[c0] Le budget atteignait 10 millions d'euros en 2026.", "UNSUPPORTED"),
        ("[c0] Le budget atteint 1000 millions d'euros en France.", "CONTRADICTED"),
    ]
    for sent, expected in cases:
        v, _ = verify_sentence(sent, ctx, NOW)
        assert v == expected, sent


def test_rounding_compatible_qualifies(ctx):
    v, _ = verify_sentence(
        "[c0] Le budget vaut environ 10 millions d'euros en France.", ctx, NOW)
    assert v in ("SUPPORTED", "PARTIALLY_SUPPORTED")


def test_hidden_unsupported_detail_rejected(ctx):
    v, reasons = verify_sentence(
        "[c1] Python 3.12 est sorti le 2 octobre 2023 à Paris.", ctx, NOW)
    assert v == "UNSUPPORTED" and any("Paris" in r for r in reasons)


def test_claim_id_spoofing_rejected(ctx):
    v, reasons = verify_sentence(
        "[c99] Le budget vaut 10 millions d'euros.", ctx, NOW)
    assert v == "UNSUPPORTED" and any("c99" in r for r in reasons)


def test_supported_composite(ctx):
    v, _ = verify_sentence(
        "[c0] [c1] En France, le budget de 10 millions coexiste avec "
        "Python 3.12 sorti en 2023.", ctx, NOW)
    assert v == "SUPPORTED_COMPOSITE"


def test_inference_exempt(ctx):
    v, _ = verify_sentence(
        "Cela pourrait probablement évoluer avec le temps.", ctx, NOW)
    assert v == "NON_FACTUAL"


def test_response_block_on_contradiction(ctx):
    out = verify_response(
        "[c0] Le budget atteint 12 millions d'euros en France.", ctx, NOW)
    assert out["overall"] == "BLOCKED"


def test_response_filtered_keeps_supported(ctx):
    out = verify_response(
        "[c0] En France, le budget atteint 10 millions d'euros en 2024. "
        "[c0] Dans le monde, le budget atteint 10 millions d'euros.", ctx, NOW)
    assert out["overall"] == "FILTERED"
    assert "Dans le monde" not in out["text"]
    assert "10 millions" in out["text"]


def test_response_exposes_evidential_conflict():
    ctx2 = build_evidence_context([
        {"claim_id": "c0", "text": "Le budget vaut 10 millions.",
         "origin": "a.example", "published_at": PUB_C0, "state": "KEEP"},
        {"claim_id": "c1", "text": "Le budget vaut 12 millions.",
         "origin": "b.example", "published_at": PUB_C0, "state": "KEEP"},
    ])
    out = verify_response("Le budget vaut 10 millions.", ctx2, NOW)
    assert out["overall"] in ("KEPT", "FILTERED")
    assert "contradictoires" in out["text"]


def test_response_block_when_gutted(ctx):
    out = verify_response(
        "[c0] Le budget vaut 50 millions. [c0] Il date de 2030.", ctx, NOW)
    assert out["overall"] == "BLOCKED"


def test_empty_context_marks_unknown():
    out = verify_response("Le budget augmente.", {}, NOW)
    assert out["overall"] == "KEPT"
    assert out["reports"][0]["verdict"] == "UNKNOWN"


# --- Contre-certification : findings figés (§4-§15, §21-§22) ---

def test_multifact_half_unproven_contaminates(ctx):
    v, _ = verify_sentence(
        "[c0] Le budget vaut 10 millions d'euros en France et B vaut 20.",
        ctx, NOW)
    assert v != "SUPPORTED" and v != "SUPPORTED_COMPOSITE"


def test_qualitative_superlative_no_free_pass(ctx):
    for s in ("Cette solution est nettement meilleure.",
              "La société connaît une forte croissance.",
              "Le produit est très populaire.",
              "C'est une technologie plus fiable que les autres."):
        v, _ = verify_sentence(s, ctx, NOW)
        assert v in ("UNSUPPORTED", "PARTIALLY_SUPPORTED", "NON_FACTUAL"), s


def test_causal_indirect_forms_rejected(ctx):
    for s in ("[c1] La sortie de Python 3.12 a permis la migration.",
              "[c1] Python 3.12 explique la migration.",
              "[c1] La migration est due à Python 3.12."):
        v, reasons = verify_sentence(s, ctx, NOW)
        assert v == "UNSUPPORTED" and any("causalité" in r for r in reasons), s


def test_present_tense_on_stale_evidence_qualified(ctx):
    v, reasons = verify_sentence("[c1] Python supporte X.", ctx, NOW)
    assert v in ("PARTIALLY_SUPPORTED", "UNSUPPORTED"), (v, reasons)


def test_sign_flip_blocked():
    from core.capabilities.truth_engine import build_evidence_context as bec
    c = bec([{"claim_id": "c0", "text": "La croissance est de 5 %.",
              "origin": "a.example", "published_at": None, "state": "KEEP"}])
    v, _ = verify_sentence("[c0] La croissance est de -5 %.", c, NOW)
    assert v == "CONTRADICTED"


def test_scale_conversions_legit():
    from core.capabilities.truth_engine import build_evidence_context as bec
    c = bec([{"claim_id": "c0", "text": "Le budget vaut 500000 euros.",
              "origin": "a.example", "published_at": None, "state": "KEEP"}])
    for s in ("[c0] Le budget vaut 0.5M d'euros.",
              "[c0] Le budget vaut 500k euros.",
              "[c0] Le budget vaut 500000,0 euros."):
        v, _ = verify_sentence(s, c, NOW)
        assert v in ("SUPPORTED", "PARTIALLY_SUPPORTED"), (s, v)


def test_meter_vs_million_regression():
    from core.capabilities.semantic_evidence import extract_measurements as em
    assert any(m.unit == "m" for m in em("La piste fait 10 m."))
    assert not any(m.unit == "m" for m in em("Le budget fait 10 millions."))
    assert any(m.unit == "millions" for m in em("Le budget fait 10 millions."))
    assert not any(m.unit == "s" for m in em("Python 3.12 sorti en 2023."))


def test_wrong_source_citation_rejected(ctx):
    v, _ = verify_sentence(
        "[c1] Le budget vaut 10 millions d'euros en France en 2024.",
        ctx, NOW)
    assert v != "SUPPORTED"  # c1 ne contient pas ce fait


def test_spoof_fuzz_rejected(ctx):
    for spoof in ("[c01]", "[cc0]", "[C0]", "[c0 ]", "[ c0]", "[c-1]",
                  "[claim0]", "[c0,c1]", "c0"):
        v, _ = verify_sentence(
            f"{spoof} Le budget vaut 10 millions.", ctx, NOW)
        assert v != "SUPPORTED" or spoof == "c0", spoof


def test_property_no_evidence_no_factual_keep():
    """§22 : sans preuve valide, jamais de KEEP factuel."""
    battery = [
        "Le budget vaut 10 millions d'euros.",
        "En 2024, la croissance était de 5 %.",
        "Python 3.12 est sorti en octobre 2023.",
        "La société ACME a doublé son chiffre d'affaires.",
        "Le produit coûte 499 € dans le monde entier.",
        "[c0] Le budget vaut 10 millions.",
    ]
    for s in battery:
        v, _ = verify_sentence(s, {}, NOW)
        assert v not in ("SUPPORTED", "SUPPORTED_COMPOSITE"), s


def test_property_conflicted_never_verified():
    """§22 : CONFLICTED ne devient jamais VERIFIED sans nouvelle preuve."""
    from core.capabilities.truth_engine import Claim, ClaimKind, verify_claim
    from core.capabilities.truth_engine import RiskTier
    c = Claim("X", kind=ClaimKind.FACT, conflicted=True)
    st, _ = verify_claim(c, RiskTier.LOW)
    assert st.value == "CONFLICTED"


# --- Hardening final : frontières §3-§18 ---

def test_unit_boundaries_m():
    from core.capabilities.truth_engine import build_evidence_context as bec
    c = bec([{"claim_id": "c0",
              "text": "La piste fait 1 million de mètres.",
              "origin": "a.example", "published_at": None, "state": "KEEP"}])
    assert verify_sentence("La piste fait 1 m.", c, NOW)[0] == "UNSUPPORTED"
    v, _ = verify_sentence("La piste fait 1 M.", c, NOW)
    assert v == "PARTIALLY_SUPPORTED"  # M ambigu : jamais PASS sec
    v2, _ = verify_sentence("La piste fait 1 million de mètres.", c, NOW)
    assert v2 == "SUPPORTED"


def test_scale_equivalences():
    from core.capabilities.truth_engine import build_evidence_context as bec
    c = bec([{"claim_id": "c0", "text": "Le total vaut 500000 euros.",
              "origin": "a.example", "published_at": None, "state": "KEEP"}])
    assert verify_sentence("[c0] Le total vaut 500k euros.", c, NOW)[0] \
        in ("SUPPORTED", "PARTIALLY_SUPPORTED")
    c2 = bec([{"claim_id": "c0", "text": "Le total vaut 1200000 euros.",
               "origin": "a.example", "published_at": None, "state": "KEEP"}])
    assert verify_sentence("[c0] Le total vaut 1.2M d'euros.", c2, NOW)[0] \
        in ("SUPPORTED", "PARTIALLY_SUPPORTED")
    c3 = bec([{"claim_id": "c0", "text": "Le total vaut 1000000000 euros.",
               "origin": "a.example", "published_at": None, "state": "KEEP"}])
    assert verify_sentence("[c0] Le total vaut 1 milliard d'euros.", c3, NOW)[0] \
        in ("SUPPORTED", "PARTIALLY_SUPPORTED")
    v, _ = verify_sentence("[c0] Le total vaut 1 billion de dollars.", c3, NOW)
    assert v == "UNSUPPORTED"  # devise non convertie, jamais silencieuse


def test_tolerance_boundaries_documented():
    """2 % = écart relatif max vs preuve même unité. Bornes exactes."""
    from core.capabilities.truth_engine import build_evidence_context as bec
    c = bec([{"claim_id": "c0", "text": "La part vaut 10 pour cent.",
              "origin": "a.example", "published_at": None, "state": "KEEP"}])
    assert verify_sentence("[c0] La part vaut 10.19 pour cent.", c, NOW)[0] \
        == "PARTIALLY_SUPPORTED"  # 1.9 % : arrondi possible
    assert verify_sentence("[c0] La part vaut 10.2 pour cent.", c, NOW)[0] \
        == "PARTIALLY_SUPPORTED"  # 2.0 % : borne incluse
    assert verify_sentence("[c0] La part vaut 10.21 pour cent.", c, NOW)[0] \
        == "CONTRADICTED"  # 2.1 % : dérive


def test_scientific_notation_understood():
    from core.capabilities.truth_engine import build_evidence_context as bec
    c = bec([{"claim_id": "c0", "text": "La valeur vaut 500.",
              "origin": "a.example", "published_at": None, "state": "KEEP"}])
    assert verify_sentence("[c0] La valeur vaut 5e2.", c, NOW)[0] == "SUPPORTED"
    c2 = bec([{"claim_id": "c0", "text": "La valeur vaut 5.",
               "origin": "a.example", "published_at": None, "state": "KEEP"}])
    assert verify_sentence("[c0] La valeur vaut 5e2.", c2, NOW)[0] \
        == "CONTRADICTED"


def test_version_vs_duration_cross():
    from core.capabilities.truth_engine import build_evidence_context as bec
    c = bec([{"claim_id": "c0", "text": "La version 3.12 est disponible.",
              "origin": "a.example", "published_at": None, "state": "KEEP"}])
    assert verify_sentence("[c0] La durée est de 3.12 seconds.", c, NOW)[0] \
        == "UNSUPPORTED"  # version ≠ durée
    c2 = bec([{"claim_id": "c0", "text": "La durée est 300 seconds.",
               "origin": "a.example", "published_at": None, "state": "KEEP"}])
    assert verify_sentence("[c0] La durée est de 5 minutes.", c2, NOW)[0] \
        == "SUPPORTED"  # conversion temps incontestable


def test_range_not_single_value():
    from core.capabilities.truth_engine import build_evidence_context as bec
    c = bec([{"claim_id": "c0", "text": "La plage est 10-20 utilisateurs.",
              "origin": "a.example", "published_at": None, "state": "KEEP"}])
    v, _ = verify_sentence("[c0] La valeur est de 15 utilisateurs.", c, NOW)
    assert v in ("UNSUPPORTED", "CONTRADICTED")  # plage ≠ valeur unique


def test_continuity_markers_on_stale():
    from core.capabilities.truth_engine import build_evidence_context as bec
    c = bec([{"claim_id": "c0", "text": "Le produit supportait X en 2024.",
              "origin": "a.example", "published_at": 1_709_000_000.0,
              "state": "KEEP"}])
    for s in ("Le produit est toujours disponible.",
              "Le produit continue de supporter X.",
              "Le produit maintient X en vigueur."):
        v, _ = verify_sentence(s, c, NOW)
        assert v in ("OUT_OF_SCOPE", "PARTIALLY_SUPPORTED", "UNSUPPORTED"), s


def test_nested_clauses_worst_wins():
    from core.capabilities.truth_engine import build_evidence_context as bec
    c = bec([{"claim_id": "c0",
              "text": "A est X en France. A a lancé Y en 2024.",
              "origin": "a.example", "published_at": None, "state": "KEEP"}])
    v, _ = verify_sentence(
        "[c0] A, qui est X en France, a lancé Y en 2024 et prévoit Z.",
        c, NOW)
    assert v in ("UNSUPPORTED", "PARTIALLY_SUPPORTED", "UNKNOWN"), v


def test_approximation_vs_conflict():
    from core.capabilities.truth_engine import build_evidence_context as bec
    c = bec([{"claim_id": "c0", "text": "La part vaut 10 pour cent.",
              "origin": "a.example", "published_at": None, "state": "KEEP"}])
    v, _ = verify_sentence("[c0] La part vaut environ 10.1 pour cent.", c, NOW)
    assert v == "PARTIALLY_SUPPORTED"  # approximation, pas conflit
