"""Tests pour core/identity/identity_context.py."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def fake_secret(monkeypatch):
    monkeypatch.setenv("EZZIO_LEDGER_SECRET", "test-secret-key-for-unit-tests")


@pytest.fixture
def identity_ctx(fake_secret):
    # Import après avoir fixé le secret
    from core.identity.identity_context import ImmutableIdentityContext
    return ImmutableIdentityContext()


class TestImmutableIdentityContextInit:
    def test_requires_secret(self, monkeypatch):
        monkeypatch.delenv("EZZIO_LEDGER_SECRET", raising=False)
        # Le module fait load_dotenv(override=True), donc on doit patcher os.getenv
        with patch("core.identity.identity_context.os.getenv", return_value=None):
            from core.identity.identity_context import ImmutableIdentityContext
            with pytest.raises(ValueError, match="EZZIO_LEDGER_SECRET"):
                ImmutableIdentityContext()

    def test_boot_session_id_format(self, identity_ctx):
        assert identity_ctx.boot_session_id.startswith("sess-")
        assert len(identity_ctx.boot_session_id) == len("sess-") + 12

    def test_boot_timestamp_is_iso(self, identity_ctx):
        from datetime import datetime
        # Doit être parsable en ISO
        datetime.fromisoformat(identity_ctx.boot_timestamp)

    def test_hashes_are_sha256(self, identity_ctx):
        for h in [
            identity_ctx.constitution_hash,
            identity_ctx.persona_hash,
            identity_ctx.lore_hash,
            identity_ctx.skill_manifest_hash,
            identity_ctx.memory_anchor_hash,
            identity_ctx.identity_root_hash,
        ]:
            assert len(h) == 64
            assert all(c in "0123456789abcdef" for c in h)

    def test_signature_is_hmac_sha256(self, identity_ctx):
        assert len(identity_ctx.signature) == 64

    def test_identity_root_differs_from_signature(self, identity_ctx):
        assert identity_ctx.identity_root_hash != identity_ctx.signature


class TestHashFile:
    def test_returns_empty_hash_for_missing(self, identity_ctx, tmp_path):
        missing = tmp_path / "nope.txt"
        h = identity_ctx._hash_file(missing)
        import hashlib
        expected = hashlib.sha256(b"EMPTY").hexdigest()
        assert h == expected

    def test_hashes_existing_file(self, identity_ctx, tmp_path):
        p = tmp_path / "x.txt"
        p.write_bytes(b"hello")
        h = identity_ctx._hash_file(p)
        import hashlib
        expected = hashlib.sha256(b"hello").hexdigest()
        assert h == expected


class TestToDict:
    def test_returns_dict_with_expected_keys(self, identity_ctx):
        d = identity_ctx.to_dict()
        assert isinstance(d, dict)
        for key in [
            "boot_session_id", "boot_timestamp",
            "constitution_hash", "persona_hash", "lore_hash",
            "skill_manifest_hash", "memory_anchor_hash",
            "identity_root_hash", "signature",
        ]:
            assert key in d, f"cle manquante: {key}"

    def test_values_are_strings(self, identity_ctx):
        d = identity_ctx.to_dict()
        for k, v in d.items():
            assert isinstance(v, str), f"{k} non-str: {type(v)}"

