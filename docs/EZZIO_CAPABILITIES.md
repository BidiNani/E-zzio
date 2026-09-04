# 🏛️ E-ZZIO — REGISTRE CANONIQUE DES CAPACITÉS OPÉRATIONNELLES

**Date de mise à jour :** 31 août 2026  
**Dépôt :** `G:\AI\E-zzio`  
**Standard :** `EVIDENCE RULE v1.1`

---

## 1. VUE D'ENSEMBLE

Ce document constitue la vue canonique et souveraine de l'ensemble des capacités, modèles, connecteurs, outils et interfaces du système E-ZzIO.

---

## 2. MODÈLES PHYSIQUES LOCAUX (OLLAMA)

| MODÈLE | TAILLE | STATUT | PREUVE | RÔLE OPÉRATIONNEL |
|---|---|---|---|---|
| `nemotron-3-nano:4b` | 2.8 GB | `ACTIVE` | `ollama list` | Candidat léger, filtrage & guardrail rapide |
| `hermes3:8b` | 4.7 GB | `ACTIVE` | `ollama list` | Conversation locale générale hors-ligne |
| `qwen3.5:9b` | 6.6 GB | `ACTIVE` | `ollama list` | Raisonnement local & parsing structuré |
| `phi4-mini:latest` | 2.5 GB | `ACTIVE` | `ollama list` | Tâches logiques concises & math |
| `nomic-embed-text:latest` | 274 MB | `ACTIVE` | `ollama list` | Vectorisation mémoire & recherche sémantique |
| `bge-m3:latest` | 1.2 GB | `ACTIVE` | `ollama list` | Indexation dense & multilingue |

---

## 3. MODÈLES CLOUD GOUVERNÉS (GEMINI POOL)

| MODÈLE | TIER | STATUT | FENÊTRE CTX | RÔLE OPÉRATIONNEL |
|---|---|---|---|---|
| `gemini-3.7-flash` | `AGENTIC_CODING` | `ACTIVE (Default)` | 1 048 576 | Développement, Agents, Architecture, Outils complexes |
| `gemini-3.5-flash` | `GENERAL` | `ACTIVE` | 1 048 576 | Conversation générale, résumés, haut débit |
| `gemini-3.5-flash-lite` | `FAST` | `ACTIVE` | 1 048 576 | Passerelle ultra-rapide (~1.1s), sous-agents, extraction |
| `gemini-3.1-pro-preview` | `DEEP_REASONING` | `ACTIVE` | 2 097 152 | Raisonnement formel approfondi, validation stricte |
| `gemini-3.1-flash-image` | `IMAGE_GEN` | `GOVERNED` | - | Synthèse d'images (Nano Banana 2) |
| `gemini-3-pro-image` | `IMAGE_GEN_PRO` | `GOVERNED` | - | Synthèse haute fidélité (Nano Banana Pro) |
| `gemini-omni-1.1-flash` | `VIDEO_GEN` | `GOVERNED` | - | Génération et édition vidéo 4K |

---

## 4. PROVIDERS LLM & CONNECTEURS EXTERNES

| PROVIDER | TYPE | IMPLÉMENTATION | AUTHENTIFICATION | STATUT |
|---|---|---|---|---|
| `gemini_pool` | Cloud LLM Pool | `core/models/gemini_pool.py` | `GEMINI_API_KEY*` (Pool 19 slots) | `ACTIVE` |
| `ollama` | Local LLM Runtime | `core/providers/ollama_provider.py` | `OLLAMA_BASE_URL` (Local) | `ACTIVE` |
| `nvidia_nim` | Cloud LLM & Vision | `core/providers/nvidia_nim_provider.py` | `NVIDIA_API_KEY` | `DORMANT` |
| `jina` | Web Reader API | `core/providers/jina_provider.py` | `JINA_API_KEY` | `DORMANT` |
| `tavily` | Web Search API | `core/providers/tavily_provider.py` | `TAVILY_API_KEY` | `DORMANT` |
| `searxng` | Local Search | `core/providers/searxng_provider.py` | `SEARXNG_BASE_URL` | `DORMANT` |
| `google_workspace` | Tools | `core/providers/google_*_provider.py` | Google OAuth / Gemini Key | `DORMANT` |

---

## 5. CAPACITÉS PERCEPTUELLES, OUTILS & FICHIERS

| CAPACITÉ | IMPLÉMENTATION | FORMATS / SERVICES | STATUT |
|---|---|---|---|
| **Lecteur Universel** | `core/perception/universal_reader.py` | PDF, DOCX, XLSX, PPTX, CSV, JSON, MD, TXT, ZIP, TAR | `TEST_VERIFIED` |
| **Synthèse Vocale (TTS)** | `core/voice/voice_gateway.py` | Kokoro-82M ONNX + Fallback procédural | `RUNTIME_VERIFIED` |
| **Reconnaissance Vocale (STT)** | `core/perception/audio_engine.py` | Moteur audio / Whisper local | `CODE_PROVEN` |
| **Vision & OCR** | `core/perception/vision_engine.py` | OCR & vision multimodale | `CODE_PROVEN` |
| **Mémoire Souveraine** | `core/memory/unified_gateway.py` | SQLite WAL + FTS5 + Vecteurs | `RUNTIME_PROVEN` |
| **Sécurité des Secrets** | `core/security/secrets_vault.py` | Chiffrement au repos & déchiffrement RAM | `RUNTIME_PROVEN` |

---

## 6. INTERFACES D'ACCÈS

- **Discord Bot :** `src/ezzio/connectors/discord_bot.py` (Mode conversationnel naturel dans le BUS)
- **Web HUD :** `src/ezzio/ui/index.html` (Interface web FastAPI)
- **CLI Commander :** `core/pc_commander.py`
- **HTTP REST API :** `src/ezzio/api.py`
- **Python SDK :** `core/sdk.py`
