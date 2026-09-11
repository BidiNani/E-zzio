"""Garde owner : DM propriétaire accepté, inconnu rejeté, espaces tolérés.

Les IDs factices ci-dessous sont arbitraires et auto-cohérents ;
seul test_real_owner_wiring touche la vraie constante chargée.
"""
from core.config import secrets_loader
from core.config.secrets_loader import DISCORD_OWNER_ID, is_owner_id

DUMMY_OWNER = "123456789012345678"


def test_owner_constant_typed():
    assert DISCORD_OWNER_ID is None or isinstance(DISCORD_OWNER_ID, int)


def test_owner_dm_accepted():
    assert is_owner_id(DUMMY_OWNER, DUMMY_OWNER) is True
    assert is_owner_id(int(DUMMY_OWNER), DUMMY_OWNER) is True


def test_stranger_dm_rejected():
    assert is_owner_id("999999", DUMMY_OWNER) is False
    assert is_owner_id("", DUMMY_OWNER) is False
    assert is_owner_id(None, DUMMY_OWNER) is False
    assert is_owner_id(DUMMY_OWNER, None) is False


def test_spaces_and_quotes_robustness():
    assert is_owner_id("  123456789012345678  ", "123456789012345678") is True
    assert is_owner_id("123456789012345678", "  123456789012345678\n") is True


def test_real_owner_wiring():
    """La constante chargée depuis secrets/.env s'auto-valide."""
    from core.config.secrets_loader import load
    load(override=False)
    from core.config import secrets_loader as sl
    assert sl.DISCORD_OWNER_ID is None or isinstance(sl.DISCORD_OWNER_ID, int)
    if sl.DISCORD_OWNER_ID is not None:
        assert sl.is_owner_id(str(sl.DISCORD_OWNER_ID)) is True
        assert sl.is_owner_id("0") is False or sl.DISCORD_OWNER_ID == 0
