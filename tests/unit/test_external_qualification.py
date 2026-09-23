"""Tests pour core/capabilities/external_qualification.py."""
from __future__ import annotations

from core.capabilities.capability_qualification import QualificationStatus
from core.capabilities.external_qualification import (
    MAX_CHAIN_DEPTH,
    MAX_DEPENDENCIES,
    ExternalCandidate,
    check_composition,
    qualify_external,
)


class TestQualifyExternal:
    def test_no_source_rejected(self):
        c = ExternalCandidate(name="x", source="", license="MIT", sandbox_verified=True)
        v = qualify_external(c)
        assert v.status == QualificationStatus.REJECTED
        assert "source" in v.reasons[0].lower()

    def test_invalid_license_rejected(self):
        c = ExternalCandidate(name="x", source="github:o/r", license="GPL-3.0")
        v = qualify_external(c)
        assert v.status == QualificationStatus.REJECTED

    def test_missing_license_rejected(self):
        c = ExternalCandidate(name="x", source="github:o/r", license=None)
        v = qualify_external(c)
        assert v.status == QualificationStatus.REJECTED

    def test_sensitive_permissions_quarantined(self):
        c = ExternalCandidate(
            name="x", source="github:o/r", license="MIT",
            permissions=["shell", "network"],
        )
        v = qualify_external(c)
        assert v.status == QualificationStatus.QUARANTINED
        assert "shell" in v.reasons[0]

    def test_too_many_dependencies_quarantined(self):
        c = ExternalCandidate(
            name="x", source="github:o/r", license="MIT",
            dependencies=[f"dep{i}" for i in range(MAX_DEPENDENCIES + 1)],
        )
        v = qualify_external(c)
        assert v.status == QualificationStatus.QUARANTINED

    def test_no_sandbox_returns_candidate(self):
        c = ExternalCandidate(
            name="x", source="github:o/r", license="MIT",
            has_tests=True, sandbox_verified=False,
        )
        v = qualify_external(c)
        assert v.status == QualificationStatus.CANDIDATE

    def test_all_conditions_met_qualified(self):
        c = ExternalCandidate(
            name="x", source="github:o/r", license="MIT",
            has_tests=True, sandbox_verified=True,
        )
        v = qualify_external(c)
        assert v.status == QualificationStatus.QUALIFIED


class TestCheckComposition:
    def test_simple_chain_ok(self):
        result = check_composition(["a", "b", "c"])
        assert result["ok"] is True
        assert result["depth"] == 3

    def test_cycle_detected(self):
        result = check_composition(["a", "b", "a"])
        assert result["ok"] is False
        assert "cycle" in result["error"].lower()

    def test_too_deep(self):
        chain = [f"x{i}" for i in range(MAX_CHAIN_DEPTH + 1)]
        result = check_composition(chain)
        assert result["ok"] is False
        assert "profondeur" in result["error"].lower()

    def test_empty_chain(self):
        result = check_composition([])
        assert result["ok"] is True
        assert result["depth"] == 0

