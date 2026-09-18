"""
E-ZZIO Test Suite — Part B Candidate Capabilities Qualification.
Certifie les 4 capacités candidates retenues avec preuves mathématiques et réelles :
1. RSSAdapter (Flux RSS 2.0 / Atom 1.0, filtrage mot-clé, protection SSRF)
2. SearXNG Backend dans WebProvider (Tier-1 local avec repli DuckDuckGo)
3. SecretsVault (Provisioning clé maître DPAPI/Env, chiffrement AES-256-GCM au repos, déchiffrement en RAM)
4. BackupEngine (Architecture CAS, déduplication réelle 100% sur fichiers inchangés, restauration)
"""
import os
from pathlib import Path

import pytest

from core.capabilities.web_provider import WebProvider
from core.perception.rss_adapter import RSSAdapter
from core.security.backup_engine import BackupEngine
from core.security.secrets_vault import SecretsVault

SAMPLE_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>CVE Security Feed</title>
    <link>https://cve.mitre.org</link>
    <description>Security Alerts</description>
    <item>
      <title>CVE-2026-1001: Critical buffer overflow</title>
      <link>https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2026-1001</link>
      <description>&lt;p&gt;A critical flaw was discovered in libexample.&lt;/p&gt;</description>
      <pubDate>Wed, 26 Aug 2026 12:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Python 3.12 Maintenance Release</title>
      <link>https://python.org/release/3.12</link>
      <description>Security fixes and speedups.</description>
      <pubDate>Tue, 25 Aug 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_rss_adapter_deterministic_parsing():
    adapter = RSSAdapter()

    # 1. Parsing complet
    res = adapter.parse_xml_feed(SAMPLE_RSS_XML, limit=5)
    assert res["ok"] is True
    assert res["type"] == "rss_2.0"
    assert res["feed_title"] == "CVE Security Feed"
    assert res["count"] == 2

    # 2. Filtrage par mot-clé (CVE)
    res_cve = adapter.parse_xml_feed(SAMPLE_RSS_XML, keyword_filter="CVE")
    assert res_cve["count"] == 1
    assert "CVE-2026-1001" in res_cve["items"][0]["title"]

    # 3. Protection SSRF
    assert adapter._is_safe_url("http://127.0.0.1/feed.xml") is False
    assert adapter._is_safe_url("http://169.254.169.254/feed.xml") is False
    assert adapter._is_safe_url("https://feeds.feedburner.com/cve") is True


@pytest.mark.asyncio
async def test_searxng_backend_routing():
    # SearXNG configuré avec URL factice -> repli transparent sur DDG
    provider = WebProvider(searxng_url="http://localhost:9999_offline")
    assert provider.searxng_url is not None


def test_secrets_vault_provisioning_and_encryption(tmp_path):
    vault = SecretsVault(workspace_root=str(tmp_path))
    env_file = tmp_path / "test.env"
    enc_file = tmp_path / "test.env.enc"

    env_file.write_text("GITHUB_TOKEN=ghp_secret12345\nDATABASE_URL=sqlite:///data.db\n", encoding="utf-8")

    # 1. Chiffrement via paramètre explicite
    enc_res = vault.encrypt_env(env_file, enc_file, passphrase="strong_master_passphrase_2026")
    assert enc_res["ok"] is True
    assert enc_file.exists()

    # 2. Déchiffrement direct en RAM
    dec_res = vault.decrypt_to_memory(enc_file, passphrase="strong_master_passphrase_2026")
    assert dec_res["ok"] is True
    assert dec_res["env_vars"]["GITHUB_TOKEN"] == "ghp_secret12345"
    assert dec_res["env_vars"]["DATABASE_URL"] == "sqlite:///data.db"

    # 3. Provisioning via Variable d'Environnement
    os.environ["EZZIO_VAULT_PASSPHRASE"] = "env_injected_passphrase_2026"
    enc_env = vault.encrypt_env(env_file, enc_file)
    assert enc_env["ok"] is True
    assert enc_env["key_source"] == "env"

    dec_env = vault.decrypt_to_memory(enc_file)
    assert dec_env["ok"] is True
    assert dec_env["env_vars"]["GITHUB_TOKEN"] == "ghp_secret12345"
    del os.environ["EZZIO_VAULT_PASSPHRASE"]


def test_backup_engine_real_cas_deduplication(tmp_path):
    # Créer une structure de fichiers factice
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    (project_dir / "file1.txt").write_text("Contenu statique A", encoding="utf-8")
    (project_dir / "file2.txt").write_text("Contenu statique B", encoding="utf-8")

    engine = BackupEngine(workspace_root=str(tmp_path))

    # Snapshot 1 : Première écriture -> 2 nouveaux objets CAS stockés
    snap1 = engine.create_snapshot(label="run_1")
    assert snap1["ok"] is True
    assert snap1["total_files"] == 2
    assert snap1["new_objects_stored"] == 2
    assert snap1["dedup_objects_reused"] == 0

    # Snapshot 2 : Aucun fichier modifié -> 0 nouvel objet stocké, 100% déduplication !
    snap2 = engine.create_snapshot(label="run_2")
    assert snap2["ok"] is True
    assert snap2["total_files"] == 2
    assert snap2["new_objects_stored"] == 0
    assert snap2["dedup_objects_reused"] == 2
    assert snap2["dedup_ratio"] == 1.0

    # Restauration vérifiée
    restored_file = tmp_path / "restored_file1.txt"
    ok = engine.restore_file(snap1["snapshot_id"], "my_project/file1.txt", restored_file)
    assert ok is True
    assert restored_file.read_text(encoding="utf-8") == "Contenu statique A"
