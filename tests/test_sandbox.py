"""tests/test_sandbox.py - Validation du sandbox terminal et des barrières de sécurité.

Historique sécurité (01/10/2026, PROVEN) : l'ancien test exécutait réellement
``git reset --hard HEAD`` avec cwd=tmp_path ; lorsque le basetemp pytest vivait
DANS le dépôt (pytest.ini ``--basetemp=tmp_pytest``), git remontait
l'arborescence et réinitialisait le VRAI dépôt G:\\AI\\E-zzio (26 reverts
reflog). Corrections : basetemp déplacé hors dépôt, mini-dépôt git dédié pour
l'exécution réelle, et garde fail-closed dans core/sandbox.py.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from core.sandbox import SecuritySandbox

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def sandbox(tmp_path: Path) -> SecuritySandbox:
    return SecuritySandbox(workspace_root=tmp_path)


def _make_isolated_git_repo(repo_dir: Path) -> None:
    """Crée un mini-dépôt git isolé (son propre .git, hors dépôt E-ZZIO)."""
    repo_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "file.txt").write_text("v1\n", encoding="utf-8")
    env_git = ["git", "-C", str(repo_dir)]
    subprocess.run([*env_git, "init"], check=True, capture_output=True)
    subprocess.run([*env_git, "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        [*env_git, "-c", "user.name=ezzio-sandbox-test", "-c", "user.email=test@ezzio.local", "commit", "-m", "init"],
        check=True,
        capture_output=True,
    )


@pytest.mark.asyncio
async def test_blocked_command_rejected_immediately(sandbox: SecuritySandbox) -> None:
    res = await sandbox.execute("rm -rf /")
    assert res.risk_level == "blocked"
    assert res.exit_code == -1
    assert "interdite" in res.stderr


@pytest.mark.asyncio
async def test_sensitive_command_requires_explicit_approval(sandbox: SecuritySandbox, tmp_path: Path) -> None:
    cmd = "git reset --hard HEAD"
    # 1. Sans approbation explicite
    res_denied = await sandbox.execute(cmd, is_approved=False)
    assert res_denied.risk_level == "sensitive"
    assert res_denied.approved is False
    assert "approbation humaine requise" in res_denied.stderr

    # 2. Garde-fou structurel : le cwd du sandbox ne doit ni être le dépôt
    # E-ZZIO ni résider sous celui-ci (le basetemp est désormais externe).
    resolved_workspace = tmp_path.resolve()
    assert resolved_workspace != REPO_ROOT, (
        "Le workspace du sandbox ne doit jamais être le dépôt E-ZZIO"
    )
    assert REPO_ROOT not in resolved_workspace.parents, (
        "Le workspace du sandbox ne doit jamais être un sous-répertoire du dépôt E-ZZIO"
    )


@pytest.mark.asyncio
async def test_git_reset_confined_to_dedicated_repo(tmp_path: Path) -> None:
    """Le ``git reset --hard`` approuvé s'exécute UNIQUEMENT dans un
    mini-dépôt git dédié et isolé ; le dépôt E-ZZIO reste intact."""
    repo_dir = tmp_path / "sandbox_repo"
    _make_isolated_git_repo(repo_dir)

    sandbox_repo = SecuritySandbox(workspace_root=repo_dir, allow_git_repo=True)
    res = await sandbox_repo.execute("git reset --hard HEAD", is_approved=True)
    assert res.risk_level == "sensitive"
    assert res.approved is True
    assert res.exit_code == 0


@pytest.mark.asyncio
async def test_git_repo_execution_fail_closed_on_real_repo(tmp_path: Path) -> None:
    """Fail-closed : toute exécution (même ``safe``) dont le cwd permet de
    découvrir le dépôt réel E-ZZIO est refusée, approbation comprise."""
    real_repo_sandbox = SecuritySandbox(workspace_root=REPO_ROOT)
    res = await real_repo_sandbox.execute("echo pwn", is_approved=True)
    assert res.risk_level == "blocked"
    assert res.exit_code == -1
    assert res.approved is False
    assert "dépôt réel" in res.stderr


@pytest.mark.asyncio
async def test_git_repo_execution_fail_closed_on_nested_cwd(tmp_path: Path) -> None:
    """Un cwd imbriqué sous le dépôt réel (ex. ancien basetemp intra-dépôt)
    est également refusé : la découverte git remonte l'arborescence."""
    nested = REPO_ROOT / "tmp_guard_probe" / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    try:
        sb = SecuritySandbox(workspace_root=tmp_path)
        res = await sb.execute("echo pwn", cwd=nested, is_approved=True)
        assert res.risk_level == "blocked"
        assert res.exit_code == -1
        assert res.approved is False
        assert "dépôt réel" in res.stderr
    finally:
        # Nettoyage du répertoire de sonde créé pour ce test uniquement.
        import shutil

        shutil.rmtree(REPO_ROOT / "tmp_guard_probe", ignore_errors=True)


@pytest.mark.asyncio
async def test_safe_command_execution(sandbox: SecuritySandbox) -> None:
    cmd = f'"{sys.executable}" -c "print(\'ezzio-ok\')"'
    res = await sandbox.execute(cmd)
    assert res.risk_level == "safe"
    assert res.approved is True
    assert res.exit_code == 0
    assert "ezzio-ok" in res.stdout
