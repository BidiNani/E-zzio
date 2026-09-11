# E-ZZIO — GUIDE DES OPERATIONS & DEPLOIEMENT

## 1. Vue d'ensemble de l'Architecture
E-ZZIO est un systeme d'intelligence artificielle souverain fonctionnant en local avec basculement Cloud resilient :
- Moteur d'inference TIER-1 : Ollama (100% CPU local, modeles Q4_K_M)
- Moteur de repli TIER-2 : Google Gemini API (Fallback automatique)
- Memoire unifiee : SQLite en mode WAL avec indexation plein texte FTS5/BM25
- Gouvernance & Securite : PromptGuard + PolicyEngine constitutionnel
- Interfaces : REST API (FastAPI), Bot Discord (Slash Commands), Passerelle Vocale (VAD/STT/TTS)

---

## 2. Prerequisites & Installation
- Python 3.12+
- Environnement virtuel : `.venv`
- Serveur Ollama actif sur `http://127.0.0.1:11434` (Optionnel pour demarrage pur Cloud)

---

## 3. Commandes Operationnelles Verifiees

### A. Lancer la passerelle API REST (FastAPI)
```bash
python -m uvicorn interfaces.api.server:app --host 0.0.0.0 --port 8000
```

### B. Verification de Disponibilite (Readiness Health Check)
```bash
curl http://127.0.0.1:8000/api/v1/health/readiness
```

### C. Executer le Test de Fumee de Deploiement (Smoke Test)
```bash
python scripts/ezzio_smoke_test.py
```

### D. Lancer le Bot Discord Souverain
*(Requiert `DISCORD_BOT_TOKEN` dans `secrets/.env`)*
```bash
python runtime/discord/bot_runner.py
```
> [!NOTE]
> En l'absence de token Discord valide, le processus s'arrete en mode securise (*fail-closed*) avec statut `DISCORD_ENVIRONMENT_LIMITED`.

---

## 4. Passerelle Vocale (Voice Gateway)
- Traitement logiciel : Operationnel (`process_voice_interaction`, VAD RMS, conteneurs WAV PCM 16-bit 16kHz).
- Peripheriques materiels d'acquisition : En environnement sans carte son physique, le systeme retourne `VOICE_HARDWARE_ENVIRONMENT_LIMITED`.

---

## 5. Procedure de Recuperation apres Incident (Recovery)
1. Panne de base SQLite : Les transactions sont protegees par le journal WAL (`evidence.db-wal`). En cas de crash, la base se reconcilie automatiquement lors de l'appel a `UnifiedMemoryGateway.init()`.
2. Panne d'un fournisseur LLM : Si Ollama est indisponible ou sature son budget de tokens, `DecisionRouter` bascule automatiquement vers Gemini ou retourne un diagnostic d'erreur explicite sans bloquer le systeme.
3. Audit de non-regression : Executer `python scripts/quality_gate.py` et `pytest -q`.
