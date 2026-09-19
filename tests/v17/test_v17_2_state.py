import pytest
from v17.state.service import product_state_service
from v17.state.models import ProductStateSnapshot

def test_v17_2_state_snapshot():
    snapshot = product_state_service.get_current_state()
    assert isinstance(snapshot, ProductStateSnapshot)
    assert snapshot.schema_version == "17.2.0"
    assert snapshot.system.readiness == "READY"
    assert snapshot.security_verdict == "FAIL_CLOSED_PROTECTED"
