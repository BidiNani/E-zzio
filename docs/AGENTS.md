# E-ZZIO Developer & Agent Operations Guide (AGENTS.md)

Ce document formalise les règles d'ingénierie et de gouvernance applicables à tout agent autonome, sous-agent CLI ou développeur intervenant sur le référentiel E-ZZIO.

---

## 🏛️ 1. Architecture & Point d'Entrée Canonique
- **Point d'accès unique en production** : `web_server.py:8001` (FastAPI / Uvicorn).
- **Interdiction formelle d'orchestration externe** : Aucun framework d'orchestration tiers (LangGraph, CrewAI, AutoGen) n'est admis. L'orchestrateur officiel unique est `CodingAgentHarness` (`core/agent/coding_agent_loop.py`).
- **Façade SDK centralisée** : Toute interaction applicative doit privilégier la façade universelle `from core import ezzio`.

---

## 🔒 2. Confinement & Gouvernance des Permissions
- **Confinement de système de fichiers** :
  - Tout accès fichier (`read_file`, `apply_patch`, `write_file`) est validé par `AgentPolicyGuard` via `os.path.commonpath`.
  - Aucun accès en dehors du workspace racine `G:\AI\E-zzio` n'est autorisé.
- **Sanctuarisation du noyau (Anti-Tampering)** :
  - Les modules critiques (`agent_guard.py`, `canonical_identity.py`, `patch_engine.py`, `tools_registry.py`, `web_server.py`, `secrets/`, `.env`, `pytest.ini`) sont protégés contre toute auto-modification par l'agent.
- **Gouvernance des Scopes (`CapabilityPolicy`)** :
  - `ALLOW` : Lecture locale, calcul procédural, recherche web sans clé.
  - `REQUIRE_HUMAN` : Écriture SaaS, déploiement externe, commandes destructives, opérations cloud à coût élevé.
  - `DENY` : Évasion de sandbox, manipulation d'identifiants de sécurité, injection shell.

---

## 🛠️ 3. Protocole d'Édition & de Self-Healing
1. **Édition chirurgicale** : Utiliser exclusivement `apply_patch` (recherche / remplacement ciblé géré par `AgentPolicyGuard`) avec génération automatique d'un snapshot atomique `.bak`. Ne jamais écraser un fichier source complet sans sauvegarde.
2. **Vérification automatique obligatoire (`pre_commit.py`)** : Toute modification de code doit impérativement être validée par l'exécution de `pre_commit.py` et des tests unitaires `pytest` avant de clôturer la tâche.
3. **Boucle d'auto-correction (Self-Healing)** : En cas d'échec de test (FAILED / ERROR), analyser le traceback, corriger le code et relancer le test (jusqu'à 3 itérations maximales avant escalade humaine).

---

## 📜 4. Journal d'Audit Immuable (Append-Only)
- Chaque action significative (exécution d'outil, décision de sécurité, modification de code) est enregistrée dans le journal scellé cryptographiquement (`audit_ledger.py`) avec liaison SHA-256.
