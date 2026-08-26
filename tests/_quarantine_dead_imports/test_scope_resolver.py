import logging
from core.scope_resolver import DomainScopeResolver


def test_scope_resolver_memory_domain():
    resolver = DomainScopeResolver()
    scope = resolver.resolve_scope("memory", max_depth=1)
    assert len(scope) > 0
    assert any("unified_gateway.py" in f for f in scope)


def test_scope_resolver_unknown_domain():
    resolver = DomainScopeResolver()
    scope = resolver.resolve_scope("unknown_domain_xyz")
    assert scope == []


def test_scope_resolver_discord_domain():
    resolver = DomainScopeResolver()
    scope = resolver.resolve_scope("discord", max_depth=1)
    assert len(scope) > 0
    assert any("bot.py" in f for f in scope)


def test_scope_resolver_router_domain_reports_missing_seeds_if_any(caplog):
    with caplog.at_level(logging.ERROR, logger="ezzio.scope_resolver"):
        resolver = DomainScopeResolver()
        scope = resolver.resolve_scope("router", max_depth=1)
        if scope == []:
            assert any("AUCUN seed" in record.message for record in caplog.records)


def test_scope_resolver_security_domain_reports_missing_seeds_if_any(caplog):
    with caplog.at_level(logging.ERROR, logger="ezzio.scope_resolver"):
        resolver = DomainScopeResolver()
        scope = resolver.resolve_scope("security", max_depth=1)
        if scope == []:
            assert any("AUCUN seed" in record.message for record in caplog.records)
