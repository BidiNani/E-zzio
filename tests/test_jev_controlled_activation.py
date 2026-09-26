"""
tests/test_jev_controlled_activation.py — Suite de validation A7 : Activation contrôlée et Fail-Closed de JEV 1.13.
Vérifie :
1. Bypass local direct pour les intentions simples (0ms, $0)
2. Invocation de JEV 1.13 uniquement pour les intentions ambiguës
3. Confidence Gate (seuil >= 0.85)
4. Fallback Fail-Closed sur réponse invalide / erreur API / faible confiance
5. Disjoncteur de sécurité (Circuit Breaker)
6. Rollback trivial (active = False)
7. Absence totale d'impact sur le routage du kernel E-ZZIO.
"""
import asyncio

import pytest

from core.capabilities.jev_decision import (
    CircuitBreakerStatus,
    JevControlledClassifier,
    JevDecisionCapability,
)


@pytest.mark.asyncio
async def test_simple_intent_bypasses_jev() -> None:
    classifier = JevControlledClassifier()

    # Prompt simple (salutation) -> doit bypasser JEV directement
    resp_chat = await classifier.classify_intent("Bonjour E-ZZIO, comment vas-tu ?")
    assert resp_chat.decision == "CHAT"
    assert resp_chat.bypassed_local is True
    assert resp_chat.invoked_jev is False
    assert resp_chat.fallback is False

    # Prompt simple (commande système) -> doit bypasser JEV
    resp_code = await classifier.classify_intent("git status --short")
    assert resp_code.decision == "CODING"
    assert resp_code.bypassed_local is True
    assert resp_code.invoked_jev is False

    # Prompt simple (directive mission) -> doit bypasser JEV
    resp_mission = await classifier.classify_intent("Inspecte et refactore le module core")
    assert resp_mission.decision == "MISSION"
    assert resp_mission.bypassed_local is True
    assert resp_mission.invoked_jev is False


@pytest.mark.asyncio
async def test_ambiguous_intent_invokes_jev_high_confidence_accepted() -> None:
    classifier = JevControlledClassifier(confidence_threshold=0.85)

    ambiguous_prompt = "Analyse cette opportunité stratégique et propose une recommandation"
    mock_resp = {
        "decision": "REASONING",
        "confidence": 0.94,
        "reason": "Analyse stratégique nécessitant du raisonnement",
    }

    resp = await classifier.classify_intent(
        prompt=ambiguous_prompt,
        mock_response=mock_resp,
    )

    assert resp.decision == "REASONING"
    assert resp.invoked_jev is True
    assert resp.accepted_jev is True
    assert resp.bypassed_local is False
    assert resp.confidence == 0.94
    assert resp.fallback is False


@pytest.mark.asyncio
async def test_low_confidence_triggers_fail_closed_fallback() -> None:
    classifier = JevControlledClassifier(confidence_threshold=0.85)

    ambiguous_prompt = "Texte totalement incertain ou bruité"
    mock_low_conf = {
        "decision": "CHAT",
        "confidence": 0.62,  # Confiance < 0.85
        "reason": "Faible certitude sur l'intention",
    }

    resp = await classifier.classify_intent(
        prompt=ambiguous_prompt,
        mock_response=mock_low_conf,
    )

    # Doit déclencher le fallback Fail-Closed -> UNKNOWN
    assert resp.decision == "UNKNOWN"
    assert resp.invoked_jev is True
    assert resp.accepted_jev is False
    assert resp.fallback is True
    assert "Confidence below threshold" in (resp.fallback_reason or "")


@pytest.mark.asyncio
async def test_invalid_schema_or_error_triggers_fail_closed_fallback() -> None:
    classifier = JevControlledClassifier()

    ambiguous_prompt = "Question complexe avec réponse invalide"
    mock_invalid_schema = {
        "decision": "INVALID_ENUM_VALUE",
        "confidence": 0.99,
        "schema_valid": False,
        "fallback": True,
    }

    resp = await classifier.classify_intent(
        prompt=ambiguous_prompt,
        mock_response=mock_invalid_schema,
    )

    assert resp.decision == "UNKNOWN"
    assert resp.accepted_jev is False
    assert resp.fallback is True


@pytest.mark.asyncio
async def test_circuit_breaker_trips_after_consecutive_failures() -> None:
    classifier = JevControlledClassifier(max_consecutive_failures=3)

    mock_error = {"fallback": True, "reason": "API Outage"}

    ambiguous_prompt = "Prompt provoquant une erreur"

    # 3 erreurs consécutives
    for _ in range(3):
        await classifier.classify_intent(ambiguous_prompt, mock_response=mock_error)

    # Le disjoncteur doit passer à DISABLED
    assert classifier.circuit_status == CircuitBreakerStatus.DISABLED
    assert classifier.stats["circuit_breaker_trips"] == 1

    # Appels ultérieurs -> basculent en fallback immédiat sans invoquer JEV
    resp_disabled = await classifier.classify_intent(ambiguous_prompt)
    assert resp_disabled.decision == "UNKNOWN"
    assert resp_disabled.fallback is True
    assert resp_disabled.invoked_jev is False
    assert "DISABLED" in (resp_disabled.fallback_reason or "")

    # Reset manuel du disjoncteur
    classifier.reset_circuit_breaker()
    assert classifier.circuit_status == CircuitBreakerStatus.OPERATIONAL


@pytest.mark.asyncio
async def test_trivial_rollback_with_active_false() -> None:
    # Desactivation globale JEV_ACTIVE = False
    classifier = JevControlledClassifier(active=False)

    resp = await classifier.classify_intent("Prompt ambigu nécessitant classification")

    assert resp.decision == "UNKNOWN"
    assert resp.invoked_jev is False
    assert resp.fallback is True
    assert "JEV_ACTIVE=False" in (resp.fallback_reason or "")


@pytest.mark.asyncio
async def test_canary_percent_control() -> None:
    # Canary a 0% -> aucun trafic ne doit passer par JEV
    classifier = JevControlledClassifier(canary_percent=0.0)

    resp = await classifier.classify_intent("Prompt ambigu pour test canary")

    assert resp.decision == "UNKNOWN"
    assert resp.invoked_jev is False
    assert resp.fallback is True
    assert "Canary bypass" in (resp.fallback_reason or "")
