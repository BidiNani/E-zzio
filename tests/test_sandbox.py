"""tests/test_sandbox.py - Validation du sandbox terminal et des barrières de sécurité."""

import sys
from pathlib import Path
import pytest
from core.sandbox import SecuritySandbox


@pytest.fixture
def sandbox(tmp_path: Path) -> SecuritySandbox:
    return SecuritySandbox(workspace_root=tmp_path)


@pytest.mark.asyncio
async def test_blocked_command_rejected_immediately(sandbox: SecuritySandbox) -> None:
    res = await sandbox.execute("rm -rf /")
    assert res.risk_level == "blocked"
    assert res.exit_code == -1
    assert "interdite" in res.stderr


@pytest.mark.asyncio
async def test_sensitive_command_requires_explicit_approval(sandbox: SecuritySandbox) -> None:
    cmd = "git reset --hard HEAD"
    # 1. Sans approbation explicite
    res_denied = await sandbox.execute(cmd, is_approved=False)
    assert res_denied.risk_level == "sensitive"
    assert res_denied.approved is False
    assert "approbation humaine requise" in res_denied.stderr

    # 2. Avec approbation explicite (exécutée sans blocage de sécurité)
    res_approved = await sandbox.execute(cmd, is_approved=True)
    assert res_approved.risk_level == "sensitive"
    assert res_approved.approved is True


@pytest.mark.asyncio
async def test_safe_command_execution(sandbox: SecuritySandbox) -> None:
    cmd = f'"{sys.executable}" -c "print(\'ezzio-ok\')"'
    res = await sandbox.execute(cmd)
    assert res.risk_level == "safe"
    assert res.approved is True
    assert res.exit_code == 0
    assert "ezzio-ok" in res.stdout
