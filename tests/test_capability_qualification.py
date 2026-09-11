"""
Test de validation du contrat de qualification des capacités (Capability Qualification).
"""
import pytest
from core.capabilities.capability_qualification import CapabilityQualification, QualificationStatus


def test_capability_qualification_schema_valid():
    qualif = CapabilityQualification(
        name="web-search-mcp",
        category="web",
        provider="brave_search_mcp",
        input_contract={"query": "str", "limit": "int"},
        output_contract={"results": "list[dict]"},
        network_access=True,
        ssrf_protection=True,
        timeout_seconds=10.0,
        status=QualificationStatus.QUALIFIED,
        tests_reference=["tests/test_phase6_saas_and_tools.py"]
    )
    assert qualif.name == "web-search-mcp"
    assert qualif.fail_closed is True
    assert qualif.status == QualificationStatus.QUALIFIED
    assert qualif.ssrf_protection is True
