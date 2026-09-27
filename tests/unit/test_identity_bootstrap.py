"""
Tests de reproductibilite de la couche identite.

Contexte : `core/identity/canonical_identity.py` est fail-closed. Il exige
`runtime/identity/persona.hash` et `persona.full.md`. Comme `runtime/` est
gitignore, ces fichiers disparaissent : un clone propre ne pouvait plus
construire le prompt systeme, et l'erreur ne disait pas quoi faire.

`tools/bootstrap_identity.py` regenere la couche depuis les sources SUIVIES
par git (config/persona.json, registry/persona.txt). Ces tests verrouillent
que la regenuration est reelle et que le fail-closed reste intact.
"""

import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.identity.canonical_identity import CanonicalIdentity  # noqa: E402


def _load_bootstrap():
    spec = importlib.util.spec_from_file_location(
        "bootstrap_identity", ROOT / "tools" / "bootstrap_identity.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestSourcesAreTracked:
    """La regeneration n'a de sens que si les sources sont dans git."""

    def test_persona_json_exists_and_is_hashable(self):
        p = ROOT / "config" / "persona.json"
        assert p.is_file(), "config/persona.json est la source du hash de contrat"
        assert len(hashlib.sha256(p.read_bytes()).hexdigest()) == 64

    def test_persona_txt_exists(self):
        p = ROOT / "registry" / "persona.txt"
        assert p.is_file(), "registry/persona.txt est la source de persona.full.md"
        assert len(p.read_text(encoding="utf-8").strip()) > 100


class TestGeneratedLayer:
    """Apres bootstrap, la couche existe et verifie."""

    @pytest.fixture(autouse=True)
    def _ensure(self):
        boot = _load_bootstrap()
        boot.generate()
        yield

    def test_all_contract_files_present(self):
        base = ROOT / "runtime" / "identity"
        for name in ("persona.hash", "persona.full.md", "identity.json", "identity_authority.json"):
            assert (base / name).is_file(), f"runtime/identity/{name} manquant"

    def test_persona_hash_matches_config_persona_json(self):
        boot = _load_bootstrap()
        expected = boot.sha256_file(ROOT / "config" / "persona.json")
        stored = (ROOT / "runtime" / "identity" / "persona.hash").read_text(
            encoding="utf-8"
        ).strip()
        assert stored == expected

    def test_verify_integrity_passes(self):
        CanonicalIdentity(root_dir=ROOT)._verify_integrity()

    def test_system_prompt_builds(self):
        prompt = CanonicalIdentity(root_dir=ROOT).build_system_prompt()
        assert len(prompt) > 500
        assert "BidiNani" in prompt

    def test_check_mode_reports_ok(self):
        assert _load_bootstrap().check() == 0


class TestFailClosedPreserved:
    """Le correctif ne doit pas affaiblir la verification d'integrite."""

    def test_tampered_hash_is_rejected(self):
        boot = _load_bootstrap()
        boot.generate()
        target = ROOT / "runtime" / "identity" / "persona.hash"
        original = target.read_text(encoding="utf-8")
        try:
            target.write_text("0" * 64 + "\n", encoding="utf-8")
            with pytest.raises(RuntimeError) as exc:
                CanonicalIdentity(root_dir=ROOT)._verify_integrity()
            assert "FAIL-CLOSED" in str(exc.value)
        finally:
            target.write_text(original, encoding="utf-8")

    def test_missing_hash_is_rejected(self, tmp_path):
        fake = tmp_path / "runtime" / "identity"
        fake.mkdir(parents=True)
        with pytest.raises(RuntimeError) as exc:
            CanonicalIdentity(root_dir=tmp_path)._verify_integrity()
        assert "FAIL-CLOSED" in str(exc.value)

    def test_bootstrap_check_detects_deletion(self):
        boot = _load_bootstrap()
        boot.generate()
        target = ROOT / "runtime" / "identity" / "persona.hash"
        original = target.read_text(encoding="utf-8")
        try:
            target.unlink()
            assert boot.check() == 1
        finally:
            target.write_text(original, encoding="utf-8")


class TestDoctorSurfacesIdentity:
    def test_doctor_reports_identity_section(self):
        from core.observability.doctor import EzzioDoctor

        _load_bootstrap().generate()
        results = EzzioDoctor(workspace_root=str(ROOT)).diagnose()
        assert "IDENTITE" in results
        assert results["IDENTITE"]["status"] in ("PROVEN", "DEGRADED")
        assert "remedy" in results["IDENTITE"]["details"]


class TestScriptIsRunnable:
    def test_help_exits_zero(self):
        p = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "bootstrap_identity.py"), "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert p.returncode == 0
        assert "--check" in p.stdout
