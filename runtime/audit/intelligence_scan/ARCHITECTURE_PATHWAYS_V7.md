# E-ZZIO V7 — Matrice d'Analyse d'Exécution Réelle
**Date :** 2026-08-11T15:34:38.720592
**Total fichiers classifiés :** 1167

## 1. Bilan par Statut d'Architecture
- 🟢 **ACTIF_CANONIQUE** : 945 fichiers
- 🟡 **ACTIF_LEGACY** : 8 fichiers
- 🔵 **HISTORIQUE_TEST** : 181 fichiers
- 🔴 **ORPHELIN_REEL** : 33 fichiers

## 2. Liste des Fichiers Identifiés comme 🔴 ORPHELIN_REEL
*(Aucun import Python entrant, aucune référence PowerShell, non monté sur web_server.py)*

- `run_ezzio.py` (Domaine: SUPPORT_TESTS)
- `routers/actions.py` (Domaine: API_ROUTERS)
- `routers/admin_maintenance.py` (Domaine: API_ROUTERS)
- `routers/autonomy.py` (Domaine: AUTONOMY_PLANNING)
- `routers/brain.py` (Domaine: API_ROUTERS)
- `routers/brain_gateway.py` (Domaine: API_ROUTERS)
- `routers/chat.py` (Domaine: API_ROUTERS)
- `routers/cloud.py` (Domaine: API_ROUTERS)
- `routers/cloud_brain.py` (Domaine: API_ROUTERS)
- `routers/ezzio_identity.py` (Domaine: PERSONA_IDENTITY)
- `routers/ezzio_unified.py` (Domaine: API_ROUTERS)
- `routers/forge.py` (Domaine: API_ROUTERS)
- `routers/human_chat.py` (Domaine: API_ROUTERS)
- `routers/human_loop.py` (Domaine: API_ROUTERS)
- `routers/knowledge.py` (Domaine: API_ROUTERS)
- `routers/memory.py` (Domaine: MEMORY_PERSISTENCE)
- `routers/models.py` (Domaine: API_ROUTERS)
- `routers/omni_bridge.py` (Domaine: API_ROUTERS)
- `routers/pc_commander.py` (Domaine: API_ROUTERS)
- `routers/performance.py` (Domaine: API_ROUTERS)
- `routers/safe_actions.py` (Domaine: API_ROUTERS)
- `routers/skills.py` (Domaine: AUTONOMY_PLANNING)
- `routers/supervisor.py` (Domaine: API_ROUTERS)
- `routers/ui_dashboard.py` (Domaine: API_ROUTERS)
- `routers/vision.py` (Domaine: API_ROUTERS)
- `routers/vision_smart.py` (Domaine: API_ROUTERS)
- `tests/conftest.py` (Domaine: SUPPORT_TESTS)
- `tests/__init__.py` (Domaine: SUPPORT_TESTS)
- `tools/patch_engine.py` (Domaine: SUPPORT_TESTS)
- `tools/fs_tools.py` (Domaine: SUPPORT_TESTS)
- `tools/workspace_index_v2.py` (Domaine: SUPPORT_TESTS)
- `tools/workspace_index_v3.py` (Domaine: SUPPORT_TESTS)
- `tools/index_engine_v5_5.py` (Domaine: SUPPORT_TESTS)

## 3. Cartographie des Routeurs FastAPI

- `routers/actions.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/admin_maintenance.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/autonomy.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/brain.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/brain_gateway.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/chat.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/cloud.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/cloud_brain.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/compress.py` -> Statut: 🟢 ACTIF_CANONIQUE (Appels PS: 0)
- `routers/ezzio_identity.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/ezzio_unified.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/forge.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/human_chat.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/human_loop.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/knowledge.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/master.py` -> Statut: 🟢 ACTIF_CANONIQUE (Appels PS: 0)
- `routers/memory.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/models.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/omni_bridge.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/omnipresence.py` -> Statut: 🟢 ACTIF_CANONIQUE (Appels PS: 0)
- `routers/pc_commander.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/performance.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/safe_actions.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/skills.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/supervisor.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/system.py` -> Statut: 🟢 ACTIF_CANONIQUE (Appels PS: 0)
- `routers/ui_dashboard.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/vision.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)
- `routers/vision_smart.py` -> Statut: 🔴 ORPHELIN_REEL (Appels PS: 0)