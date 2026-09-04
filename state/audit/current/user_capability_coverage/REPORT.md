# 🏛️ E-ZZIO — RAPPORT D'AUDIT DE COUVERTURE FONCTIONNELLE UTILISATEUR

**Date :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`  
**Objet :** Cartographie exhaustive des actions utilisateur réelles à travers Discord, HTTP API, CLI et Web HUD

---

## 1. CARTOGRAPHIE D'ACCÈS PAR INTERFACE

| CAPACITÉ | DISCORD | HTTP API | CLI / SDK | WEB HUD | STATUT |
|---|---|---|---|---|---|
| **Chat & Raisonnement** | `!bidi <texte>` | `POST /master/chat` | `ezzio_cli.py` | Chat temps réel | **OPERATIONAL** |
| **Recherche Web** | Automatique | `POST /perception/perceive` | Automatique | Automatique (via chat) | **OPERATIONAL** |
| **Lecture d'URLs** | URLs détectées | `POST /perception/perceive` | Trajectoire | Automatique (via chat) | **OPERATIONAL** |
| **Documents (PDF, DOCX, XLSX)** | Pièces jointes | `POST /perception/upload` | Ingestion | Upload API | **OPERATIONAL** |
| **Mémoire (FTS5 / Rappel)** | `!bidi recall <q>` | `POST /memory/search` | Interne | Statut dans `/metrics` | **OPERATIONAL** |
| **Vision Multimodale** | Images jointes | `POST /perception/upload` | Trajectoire | Vision intégrée | **OPERATIONAL** |
| **Synthèse Vocale (TTS)** | Vocal bot | `POST /generators/audio/tone` | Trajectoire | Lecteur audio | **OPERATIONAL** |
| **Transcription (STT)** | Audio joint | `POST /perception/upload` | Trajectoire | API upload | **OPERATIONAL** |
| **Google Workspace** | Read-Only | `POST /capabilities/execute` | Optionnel | Optionnel | **CONFIG_REQUIRED** |
| **GitHub** | Read-Only | `POST /capabilities/execute` | Optionnel | Optionnel | **CONFIG_REQUIRED** |

---

## 2. GAPS IDENTIFIÉS & PISTES D'AMÉLIORATION

1. **Web HUD File Dropper :** L'API `POST /perception/upload` est 100% opérationnelle, mais l'interface graphique du Web HUD ne dispose pas encore de bouton de glisser-déposer explicite.
2. **Documentation Discord :** Les commandes `!bidi recall` et `!bidi status` sont actives mais méritent une section dédiée dans la documentation utilisateur.
3. **Workspace OAuth :** Les connecteurs sont prêts et sécurisés en lecture seule, en attente de tokens utilisateur dans `secrets/.env`.
