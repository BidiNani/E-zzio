# E-ZZIO V9.0 — TEST ECONOMY & DECOMPOSITION

**Date de Mesure** : 29 août 2026

---

## 1. DÉCOMPOSITION EXACTE DE LA SUITE DE TESTS
- **Nombre de fichiers de test (`test_*.py`)** : **104 fichiers**
- **Nombre de fonctions de test uniques (AST `test_*`)** : **173 fonctions brutes**
- **Nombre d'items de test collectés & exécutés (Pytest)** : **311 items** (via matrices `@pytest.mark.parametrize`)
- **Résultat d'exécution** : **311 passed / 0 failed / 0 skipped en 73.49s**

---

## 2. TAXONOMIE PAR VALEUR CONTRACTUELLE

| Catégorie | Fichiers Représentatifs | Rôle Contractuel | Valeur |
| :--- | :--- | :--- | :---: |
| **`ARCHITECTURE GUARDS`** | `test_architecture_freeze.py`, `test_architecture_drift.py` | Immunité contre dérive, 7 routeurs, mono-autorité | **CRITIQUE** |
| **`SECURITY & GOVERNANCE`** | `test_capability_policy.py`, `test_security_governance.py` | Validation `ALLOW`/`REQUIRE_HUMAN`/`DENY` | **CRITIQUE** |
| **`COGNITIVE & LLM`** | `test_gemini_pool.py`, `test_model_router_failure_matrix.py` | Rotation 429 instantanée, sélection profil | **ÉLEVÉE** |
| **`MEMORY & EVIDENCE`** | `test_unified_memory_gateway.py`, `test_fts5_memory.py` | Persistance WAL, indexation FTS5 L0-L5 | **ÉLEVÉE** |
| **`CAPABILITIES & IO`** | `test_youtube_perception_qualification.py`, `test_safe_fetcher.py`| Parsing YouTube direct, anti-SSRF | **ÉLEVÉE** |
| **`STARTUP & OFFLINE`** | `test_ollama_nonblocking_startup.py`, `test_startup_with_all_backends_offline.py` | Vivacité boot avec backends distants coupés | **CRITIQUE** |
