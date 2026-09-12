"""
tests/test_data_capability.py — Unit tests for Data Capabilities, DataSourceManager, SQL Security & Provenance.
"""
import pytest
from core.agent.capability_manager import CapabilityManager
from core.agent.data_source_manager import (
    DataSourceManager, DataSourceRecord, DataSourceType, data_source_manager
)

def test_capability_data_permissions():
    mgr = CapabilityManager()

    data_prof = mgr.get_profile("DATA_ANALYSIS")
    assert data_prof.role == "DATA_ANALYSIS"
    assert "database.read" in data_prof.permissions
    assert "database.query" in data_prof.permissions
    assert "data.provenance" in data_prof.permissions

    forensic = mgr.get_profile("FORENSIC")
    assert "database.read" in forensic.permissions

def test_data_source_priority_hierarchy():
    dsm = DataSourceManager()

    # Enregistrement de sources factices représentant la hiérarchie
    dsm.register_source(DataSourceRecord(
        source_id="paid_cloud_db",
        name="Paid Cloud DB",
        source_type=DataSourceType.PAID_CLOUD,
        location="https://cloud.db/paid"
    ))
    dsm.register_source(DataSourceRecord(
        source_id="open_data_api",
        name="Open Data API",
        source_type=DataSourceType.OPEN_DATA_API,
        location="https://api.gouv.fr/data"
    ))

    # discovery privilégie LOCAL_SQLITE / OPEN_DATA_API par rapport à PAID_CLOUD
    best = dsm.discover_best_source()
    assert best is not None
    assert best.source_type in [DataSourceType.LOCAL_SQLITE, DataSourceType.OPEN_DATA_API]

def test_sql_parameterized_query_and_read_only():
    dsm = DataSourceManager()

    # Test d'exécution paramétrée sécurisée
    res = dsm.execute_parameterized_sql(
        source_id="local_evidence_db",
        sql_query="SELECT COUNT(*) as count FROM sqlite_master WHERE type=?;",
        params=("table",),
        is_write=False,
        agent_permissions=["database.read"]
    )
    assert res["ok"] is True
    assert "count" in res

    # Contrôle de permission : tentative d'écriture sans permission -> REFUSED
    res_write_denied = dsm.execute_parameterized_sql(
        source_id="local_evidence_db",
        sql_query="UPDATE evidence_store SET status='test';",
        params=(),
        is_write=True,
        agent_permissions=["database.read"]  # pas de database.write
    )
    assert res_write_denied["ok"] is False
    assert "PERMISSION_DENIED" in res_write_denied["error"]

def test_sql_ddl_security_block():
    dsm = DataSourceManager()

    res_ddl = dsm.execute_parameterized_sql(
        source_id="local_evidence_db",
        sql_query="DROP TABLE session_messages;",
        params=(),
        is_write=True,
        agent_permissions=["database.read", "database.write"]
    )
    assert res_ddl["ok"] is False
    assert "SECURITY_BLOCK" in res_ddl["error"]

if __name__ == "__main__":
    test_capability_data_permissions()
    test_data_source_priority_hierarchy()
    test_sql_parameterized_query_and_read_only()
    test_sql_ddl_security_block()
    print("✅ ALL DATA CAPABILITY & SECURITY TESTS PASSED")
