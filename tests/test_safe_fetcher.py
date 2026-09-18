"""
Tests unitaires pour le SafeWebFetcher et la protection Anti-SSRF.
"""

import pytest

from core.perception.safe_fetcher import SafeWebFetcher, SSRFSecurityError


@pytest.mark.asyncio
async def test_ssrf_blocking_localhost_and_internal_ips():
    fetcher = SafeWebFetcher()

    # 1. Test blocage direct 127.0.0.1 (API interne E-ZzIO)
    res_local = await fetcher.fetch_url("http://127.0.0.1:8001/health")
    assert res_local["ok"] is False
    assert res_local["status"] == "SSRF_BLOCKED"
    assert "interdit" in res_local["error"]

    # 2. Test blocage localhost
    res_host = await fetcher.fetch_url("http://localhost:8080/secret")
    assert res_host["ok"] is False
    assert res_host["status"] == "SSRF_BLOCKED"

    # 3. Test blocage IP privée 192.168.x.x
    res_priv = await fetcher.fetch_url("http://192.168.1.1/admin")
    assert res_priv["ok"] is False
    assert res_priv["status"] == "SSRF_BLOCKED"

    # 4. Test blocage IP privée 10.0.x.x
    res_priv10 = await fetcher.fetch_url("http://10.0.0.5/api")
    assert res_priv10["ok"] is False
    assert res_priv10["status"] == "SSRF_BLOCKED"


def test_ip_safety_checker():
    fetcher = SafeWebFetcher()

    # Adresses interdites
    assert fetcher.is_ip_allowed("127.0.0.1") is False
    assert fetcher.is_ip_allowed("10.0.0.1") is False
    assert fetcher.is_ip_allowed("192.168.1.50") is False
    assert fetcher.is_ip_allowed("172.20.0.1") is False
    assert fetcher.is_ip_allowed("169.254.169.254") is False
    assert fetcher.is_ip_allowed("0.0.0.0") is False

    # Adresses publiques autorisées
    assert fetcher.is_ip_allowed("8.8.8.8") is True
    assert fetcher.is_ip_allowed("1.1.1.1") is True
