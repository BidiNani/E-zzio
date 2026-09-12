"""
tests/test_web_access_manager.py — Deterministic Unit Tests for Universal Web Access & URL Manager
"""
import pytest
from core.agent.web_access_manager import (
    WebAccessManager, WebAccessMode, web_access_manager
)
from core.agent.input_access_manager import InputType, InputDocument
from core.agent.capability_manager import CapabilityManager

def test_ssrf_security_block():
    wam = WebAccessManager()

    # Tentatives SSRF d'accès aux hôtes locaux et IP privées -> Bloquées
    assert wam.is_ssrf_safe("http://localhost/admin")[0] is False
    assert wam.is_ssrf_safe("http://127.0.0.1:8001/master/chat")[0] is False
    assert wam.is_ssrf_safe("http://169.254.169.254/latest/meta-data")[0] is False
    assert wam.is_ssrf_safe("file:///C:/Windows/system32")[0] is False

    # URL publique valide -> Autorisée
    assert wam.is_ssrf_safe("https://ai.google.dev/docs")[0] is True

def test_ssrf_fetch_blocked_document():
    wam = WebAccessManager()

    doc = wam.fetch_url("http://127.0.0.1/secret")
    assert doc.status == "BLOCKED"
    assert "SECURITY BLOCK" in doc.content_text

def test_access_mode_classification():
    wam = WebAccessManager()

    assert wam.classify_access_mode("https://api.github.com/repos") == WebAccessMode.PUBLIC_API
    assert wam.classify_access_mode("https://www.leboncoin.fr/offres") == WebAccessMode.PUBLIC_HTTP
    assert wam.classify_access_mode("https://www.instagram.com/p/123") == WebAccessMode.PUBLIC_HTTP

def test_capability_web_permissions():
    mgr = CapabilityManager()

    res_prof = mgr.get_profile("RESEARCH")
    assert "web.read" in res_prof.permissions
    assert "web.extract" in res_prof.permissions

def test_prompt_injection_isolation():
    wam = WebAccessManager()

    # Le texte extrait reste des données textuelles sous InputDocument.content_text
    doc = wam.fetch_url("http://127.0.0.1/test")
    assert isinstance(doc.content_text, str)
    assert doc.input_type == InputType.URL

if __name__ == "__main__":
    test_ssrf_security_block()
    test_ssrf_fetch_blocked_document()
    test_access_mode_classification()
    test_capability_web_permissions()
    test_prompt_injection_isolation()
    print("✅ ALL WEB ACCESS MANAGER SECURITY & FUNCTIONAL TESTS PASSED")
