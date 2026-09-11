"""Routage Discord : catégorie Bus sans préfixe, hors catégorie ignoré."""
from core.integrations.discord.routing_rules import (
    BIDINANI_BUS_CATEGORY_ID,
    channel_category_id,
    should_respond,
)


class _Chan:
    def __init__(self, category_id=None, parent=None):
        self.category_id = category_id
        self.parent = parent


def test_bus_category_no_prefix():
    ok, clean = should_respond(False, BIDINANI_BUS_CATEGORY_ID, False, "salut E-ZZIO")
    assert ok is True and clean == "salut E-ZZIO"


def test_bus_thread_via_parent():
    parent = _Chan(category_id=BIDINANI_BUS_CATEGORY_ID)
    thread = _Chan(category_id=None, parent=parent)
    assert channel_category_id(thread) == BIDINANI_BUS_CATEGORY_ID
    ok, _ = should_respond(False, channel_category_id(thread), False, "hello")
    assert ok is True


def test_outside_category_no_prefix_ignored():
    ok, _ = should_respond(False, 999999, False, "salut")
    assert ok is False


def test_outside_category_prefix_ok():
    ok, clean = should_respond(False, 999999, False, "!e ping")
    assert (ok, clean) == (True, "ping")


def test_channel_category_direct():
    assert channel_category_id(_Chan(category_id=123)) == 123
    assert channel_category_id(_Chan()) is None
