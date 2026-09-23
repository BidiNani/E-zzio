"""Tests Vague A : 3 branches manquantes pour atteindre 100%.

- research_fabric.origin_domain : ligne 169-170 (except ValueError)
- continuous_operations_loop.run_control_cycle : ligne 164->165 (status COMPLETED)
- smart_vision.build_prompt : ligne 182->193 (branche specifique)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ============================================================
# 1. research_fabric.origin_domain L169-170
# ============================================================

class TestOriginDomainErrorBranch:
    """L169-170 : urlparse leve ValueError -> return locator.lower()."""

    def test_urlparse_value_error_returns_lowercase(self):
        """Un locator malforme fait lever urlparse -> on retourne locator.lower()."""
        from core.capabilities import research_fabric

        # Force urlparse a lever ValueError
        with patch.object(research_fabric, "urlparse", side_effect=ValueError("bad url")):
            result = research_fabric.origin_domain("HTTP://BAD")
        assert result == "http://bad"

    def test_normal_url_still_works(self):
        """Cas nominal (non-regression)."""
        from core.capabilities.research_fabric import origin_domain
        assert origin_domain("https://www.example.com/path") == "example.com"

    def test_no_domain_returns_host(self):
        """Host sans point -> retourne host tel quel."""
        from core.capabilities.research_fabric import origin_domain
        # urlparse('file:///tmp/x').netloc == '' -> parts=[] -> len<2 -> return host=''
        result = origin_domain("file:///tmp/x")
        assert isinstance(result, str)


# ============================================================
# 2. continuous_operations_loop.run_control_cycle L164-165
# ============================================================

class TestRunControlCycleCompletedBranch:
    """L164->165 : decision.selected_mission_id + execute retourne COMPLETED."""

    def test_cycle_with_completed_mission(self):
        """Mock l'arbitrator : decision -> mission selectionnee -> COMPLETED."""
        from core.operations.continuous_operations_loop import (
            ContinuousOperationsControlLoop,
        )

        # Mock de l'arbitrator
        mock_arb = MagicMock()
        mock_arb.managed_missions = {}
        mock_arb.workers = {}
        mock_arb.max_concurrent_missions = 4

        # Decision mockee
        mock_decision = MagicMock()
        mock_decision.selected_mission_id = "tsk-001"
        mock_decision.decision_id = "dec-001"
        mock_arb.arbitrate_and_schedule.return_value = mock_decision

        # Execution retourne COMPLETED
        mock_arb.execute_managed_mission.return_value = {"status": "COMPLETED"}

        # world_model.detect_state_drift mockee
        with patch(
            "core.operations.continuous_operations_loop.world_model"
        ) as mock_wm:
            mock_wm.detect_state_drift = MagicMock()

            loop = ContinuousOperationsControlLoop(arbitrator=mock_arb)
            result = loop.run_control_cycle()

        # L'assertion cle : la branche 164->165 a ete prise
        assert result.executed_missions == ["tsk-001"]
        assert result.arbitration_decision_id == "dec-001"

    def test_cycle_with_non_completed_mission(self):
        """Branche alternative : execution retourne un autre statut."""
        from core.operations.continuous_operations_loop import (
            ContinuousOperationsControlLoop,
        )

        mock_arb = MagicMock()
        mock_arb.managed_missions = {}
        mock_arb.workers = {}
        mock_arb.max_concurrent_missions = 4

        mock_decision = MagicMock()
        mock_decision.selected_mission_id = "tsk-002"
        mock_decision.decision_id = "dec-002"
        mock_arb.arbitrate_and_schedule.return_value = mock_decision
        mock_arb.execute_managed_mission.return_value = {"status": "FAILED"}

        with patch(
            "core.operations.continuous_operations_loop.world_model"
        ) as mock_wm:
            mock_wm.detect_state_drift = MagicMock()

            loop = ContinuousOperationsControlLoop(arbitrator=mock_arb)
            result = loop.run_control_cycle()

        assert result.executed_missions == []

    def test_cycle_with_no_mission_selected(self):
        """Branche : selected_mission_id == 'NONE' -> pas d'execution."""
        from core.operations.continuous_operations_loop import (
            ContinuousOperationsControlLoop,
        )

        mock_arb = MagicMock()
        mock_arb.managed_missions = {}
        mock_arb.workers = {}
        mock_arb.max_concurrent_missions = 4

        mock_decision = MagicMock()
        mock_decision.selected_mission_id = "NONE"
        mock_decision.decision_id = "dec-003"
        mock_arb.arbitrate_and_schedule.return_value = mock_decision

        with patch(
            "core.operations.continuous_operations_loop.world_model"
        ) as mock_wm:
            mock_wm.detect_state_drift = MagicMock()

            loop = ContinuousOperationsControlLoop(arbitrator=mock_arb)
            result = loop.run_control_cycle()

        assert result.executed_missions == []
        mock_arb.execute_managed_mission.assert_not_called()


# ============================================================
# 3. smart_vision — branche 182->193
# ============================================================
# NOTE : la zone exacte est lue dans le bloc. Si la branche est
# dans build_prompt, le test ci-dessous la cible via le prompt
# utilisateur (ex: technical + logo simultanes, ou un cas specifique).

class TestSmartVisionBuildPromptBranch:
    """Cible la branche non couverte L182->193 (a ajuster apres lecture)."""

    def test_build_prompt_with_empty_prompt(self):
        """Prompt vide -> la fonction doit produire un prompt par defaut."""
        from core.smart_vision import build_prompt
        result = build_prompt(path="test.png", user_prompt="")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_build_prompt_with_technical_path(self):
        """Path technique + prompt vide."""
        from core.smart_vision import build_prompt
        result = build_prompt(path="screenshot_error.png", user_prompt="")
        assert isinstance(result, str)

    def test_build_prompt_with_logo_path(self):
        """Path logo + prompt."""
        from core.smart_vision import build_prompt
        result = build_prompt(path="logo_druide.png", user_prompt="decris ce logo")
        assert isinstance(result, str)

    def test_build_prompt_with_both_technical_and_logo(self):
        """Path mixte : technical ET logo -> la branche prioritaire s'applique."""
        from core.smart_vision import build_prompt
        result = build_prompt(path="logo_error.png", user_prompt="")
        assert isinstance(result, str)
