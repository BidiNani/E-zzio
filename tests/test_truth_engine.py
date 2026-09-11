"""Moteur vérité : red-team systématique — faux, manquants et conflits
restent visibles, jamais affirmés."""
from core.capabilities.truth_engine import (
    Claim, ClaimKind, EvidenceRef, EvidenceTier, GateAction, RiskTier,
    VerifState, correction_payload, has_valid_locator, mark_finding,
    response_gate, verify_claim,
)


def ev(source_id="s", locator="https://officiel.example/x", tier=None,
       retrieved=True, origin="officiel.example", **kw):
    return EvidenceRef(source_id=source_id, locator=locator,
                       tier=tier or EvidenceTier.OFFICIAL_SOURCE,
                       retrieved=retrieved, origin=origin, **kw)


def test_verified_primary_and_corrobation():
    c = Claim("X publié", sources=(ev("a"), ev("b", locator="https://a.example/y",
                                          tier=EvidenceTier.INDEPENDENT_REPUTABLE,
                                          origin="a.example")), scope_supported=True)
    st, _ = verify_claim(c, RiskTier.SENSITIVE)
    assert st == VerifState.VERIFIED
    c2 = Claim("X publié", sources=(ev("a", tier=EvidenceTier.SECONDARY_SOURCE),
                                    ev("b", locator="https://a.example/y",
                                       tier=EvidenceTier.SECONDARY_SOURCE,
                                       origin="a.example")), scope_supported=True)
    st2, _ = verify_claim(c2, RiskTier.IMPORTANT)
    assert st2 == VerifState.CORROBORATED  # 2 origines, sans primaire


def test_no_retrieval_no_fact():
    assert verify_claim(Claim("X", sources=(ev(retrieved=False),)),
                        RiskTier.LOW)[0] == VerifState.UNVERIFIED
    assert verify_claim(Claim("X"), RiskTier.LOW)[0] == VerifState.UNVERIFIED
    assert verify_claim(Claim("X", kind=ClaimKind.MEMORY_DERIVED),
                        RiskTier.LOW)[0] == VerifState.INSUFFICIENT_EVIDENCE


def test_fake_locators_rejected():
    assert has_valid_locator("") is False
    assert has_valid_locator("not a url") is False
    assert has_valid_locator("https://") is False
    assert has_valid_locator("https://reel.example/doc") is True
    assert has_valid_locator("internal:workspace/notes.md") is True
    c = Claim("X", sources=(ev(locator="article inventé"),), scope_supported=True)
    assert verify_claim(c, RiskTier.LOW)[0] == VerifState.UNVERIFIED


def test_inference_opinion_never_verified():
    c = Claim("Y probable", kind=ClaimKind.INFERENCE)
    assert verify_claim(c, RiskTier.LOW)[0] == VerifState.UNVERIFIED
    c2 = Claim("Y probable", kind=ClaimKind.PREDICTION, uncertainty_marked=True)
    assert verify_claim(c2, RiskTier.LOW)[0] == VerifState.PARTIALLY_VERIFIED
    c3 = Claim("L'utilisateur dit Z", kind=ClaimKind.USER_PROVIDED,
               sources=(ev(),))
    assert verify_claim(c3, RiskTier.LOW)[0] == VerifState.UNVERIFIED


def test_conflict_and_scope():
    c = Claim("X", sources=(ev(), ev("b")), scope_supported=True, conflicted=True)
    assert verify_claim(c, RiskTier.IMPORTANT)[0] == VerifState.CONFLICTED
    c2 = Claim("X déployé mondialement", sources=(ev(), ev("b")),
               scope_supported=False)
    st, reasons = verify_claim(c2, RiskTier.IMPORTANT)
    assert st == VerifState.PARTIALLY_VERIFIED and any("portée" in r for r in reasons)


def test_risk_scales_and_viral_is_low():
    one = Claim("X", sources=(ev(),), scope_supported=True)
    assert verify_claim(one, RiskTier.LOW)[0] == VerifState.VERIFIED
    assert verify_claim(one, RiskTier.CRITICAL)[0] == VerifState.INSUFFICIENT_EVIDENCE
    viral = Claim("Buzz", sources=(ev(tier=EvidenceTier.COMMUNITY_SOURCE,
                                      origin="social.example"),),
                  scope_supported=True)
    st, _ = verify_claim(viral, RiskTier.IMPORTANT)
    assert st == VerifState.INSUFFICIENT_EVIDENCE  # 1 voix sociale ≠ preuve


def test_response_gate_blocks_unverified():
    good = Claim("A", sources=(ev(),), scope_supported=True)
    bad = Claim("B")
    mixed_verdict, decisions = response_gate([(good, RiskTier.LOW),
                                              (bad, RiskTier.IMPORTANT)])
    assert mixed_verdict == "BLOCKED"
    acts = {d[1] for d in decisions}
    assert acts == {GateAction.KEEP, GateAction.REMOVE}
    ok_verdict, _ = response_gate([(good, RiskTier.LOW)])
    assert ok_verdict == "PASS"


def test_correction_and_expiry():
    p = correction_payload("Ancien X", VerifState.CONFLICTED, "source B contredit")
    assert p["kind"] == "CLAIM_CORRECTION" and p["new_status"] == "CONFLICTED"
    f = mark_finding("résultat", observed_at=1000.0, volatility_days=30.0)
    assert f["fresh_until"] == 1000.0 + 30 * 86400.0
    assert f["status"] == "UNVERIFIED"  # jamais promu seul


# --- Gate de sortie ---

from core.capabilities.truth_engine import (
    UNVERIFIED_NOTICE, apply_output_gate, requires_gate,
    source_results_to_claims,
)


def test_requires_gate_triggers():
    for q in ("Est-ce vrai que X ?", "Quoi de neuf sur l'IA ?",
              "Quelle est la dernière version de Y ?", "Compare A et B",
              "Qui est le PDG de Z ?", "Is it true that W ?",
              "Que s'est-il passé en 2025 ?"):
        needed, _ = requires_gate(q)
        assert needed is True, q


def test_requires_gate_quiet():
    for q in ("Bonjour", "Mets en pause la tâche", "Où en sont les tâches ?",
              "Annule la tâche", "Explique-moi ce concept",
              "Aide-moi à écrire cette fonction"):
        needed, _ = requires_gate(q)
        assert needed is False, q


def test_apply_gate_no_claims():
    v, notice = apply_output_gate("Est-ce vrai que X ?")
    assert v == "UNVERIFIED_NO_EVIDENCE" and notice == UNVERIFIED_NOTICE
    v2, n2 = apply_output_gate("Bonjour")
    assert v2 == "PASS_NON_FACTUAL" and n2 is None


def test_apply_gate_with_claims():
    good = Claim("A", sources=(ev(),), scope_supported=True)
    v, n = apply_output_gate("question", [(good, RiskTier.LOW)])
    assert v == "PASS_WITH_EVIDENCE" and n is None
    v2, n2 = apply_output_gate("question", [(Claim("B"), RiskTier.IMPORTANT)])
    assert v2 == "BLOCKED" and n2 == UNVERIFIED_NOTICE


def test_bridge_keeps_only_retrieved():
    from core.capabilities.research_fabric import SourceResult, Trust
    ok = SourceResult(source_id="s", title="t", locator="https://a.example/x",
                      content="contenu réel", trust=Trust.OFFICIAL,
                      provenance="a.example")
    ghost = SourceResult(source_id="g", title="faux", locator="article inventé",
                         content="bla", trust=Trust.UNKNOWN)
    empty = SourceResult(source_id="e", title="vide",
                         locator="https://b.example/y", content="  ",
                         trust=Trust.REPUTABLE_SECONDARY)
    claims = source_results_to_claims([ok, ghost, empty], "Q ?")
    assert len(claims) == 1
    assert claims[0][0].sources[0].tier == EvidenceTier.OFFICIAL_SOURCE


def test_gate_error_fail_closed():
    v, n = apply_output_gate(None, claims="BOGUS")  # type: ignore
    assert v == "GATE_ERROR_FAIL_CLOSED" and n == UNVERIFIED_NOTICE


def test_verify_grounding():
    from core.capabilities.truth_engine import verify_grounding
    ans = ("Résumé : 2 résultats.\n"
           "- [c0] Le budget vaut 10 millions [source : https://a.example]\n"
           "- [c1] [REMOVE] Affirmation non prouvée (aucune source).")
    assert verify_grounding(ans, ["c0", "c1"]) == ("GROUNDED", [])
    v, orphans = verify_grounding(ans + "\n- Le ciel est vert.", ["c0", "c1"])
    assert v == "UNGROUNDED" and len(orphans) == 1
    assert verify_grounding("Aucune ligne factuelle.", ["c0"]) == ("GROUNDED", [])
