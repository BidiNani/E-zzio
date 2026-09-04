# 🏛️ RUNBOOK D’EXPLOITATION QUOTIDIENNE — E-ZZIO

**Standard Opérationnel :** `EVIDENCE RULE v1.1`  
**Version Système :** `E-ZZIO 2.0 (PRODUCTION OBSERVÉE & GELÉE)`  
**Dépôt :** `G:\AI\E-zzio`

---

## ⚡ E-ZZIO EN 60 SECONDES

E-ZzIO est un système d'IA unifié souverain fonctionnant en architecture **Cloud-First** avec **Cache Sub-milliseconde**, **Singleflight Async**, **Bascule Same-Role (Groq)** et **Ollama en Dernier Recours Local**.

### Commandes Clés :
```powershell
# 1. Démarrer le Serveur Web & Web HUD (Port 8000)
python web_server.py

# 2. Démarrer le Client Discord (Optionnel)
python -m core.integrations.discord.discord_client

# 3. Vérification de santé (1 seconde)
curl http://127.0.0.1:8000/health

# 4. Métriques en direct
curl http://127.0.0.1:8000/metrics
```

---

## 1. CARTOGRAPHIE CANONIQUE DES MODÈLES ET DU ROUTAGE

Le routage est orchestré de manière unique par `ModelRouter` (`core/cognition/model_router.py`) :

| PROFIL | PRIMAIRE CLOUD (GEMINI) | SECONDAIRE CLOUD (GROQ) | DERNIER RECOURS (OLLAMA LOCAL) | CAS D'USAGE |
|---|---|---|---|---|
| **FAST** | `gemini-3.1-flash-lite` | `groq/compound-mini` | `phi4-mini:latest` | Questions rapides, extraction, classification |
| **GENERAL** | `gemini-3.6-flash` | `groq/compound` | `hermes3:8b` | Dialogue général, explications, synthèse |
| **CODING** | `gemini-3.7-flash` | `qwen/qwen3.6-27b` | `qwen3.5:9b` | Programmation, refactoring, agentique |
| **DEEP** | `gemini-3.1-pro-preview` | `openai/gpt-oss-120b` | `qwen3.5:9b` | Raisonnement complexe, mathématiques |
| **IMAGE** | `gemini-3.1-flash-image` | `gemini-3-pro-image` | N/A | Génération et édition d'images |
| **VIDEO** | `gemini-omni-1.1-flash` | N/A | N/A | Génération vidéo jusqu'à 4K |

---

## 2. PREFLIGHT EN 10 SECONDES

Avant d'entamer une session de travail quotidienne :

```powershell
# 1. Vérifier l'état git du dépôt
git -C G:\AI\E-zzio status --short

# 2. Vérifier les modèles Ollama locaux
ollama list

# 3. Vérifier la santé du serveur
curl http://127.0.0.1:8000/health
```

**Réponse attendue sur `/health` :**
```json
{
  "status": "healthy",
  "version": "2.0",
  "model_router": "operational",
  "memory_gateway": "operational"
}
```

---

## 3. UTILISATION QUOTIDIENNE PAR CANAL

### A. Web HUD (`http://127.0.0.1:8000`)
- **Chat Cognitif :** Tapez directement vos questions dans la console Web.
- **Upload Documentaire (Drag & Drop) :** Glissez-déposez vos fichiers (PDF, DOCX, XLSX, CSV, TSV, HTML, TXT, ZIP) ou cliquez sur le bouton trombone.
- **Suivi Télémétrique :** Les badges en haut à droite affichent le statut en direct de Gemini, Groq, Ollama, Cache, Latence et Quota.

### B. Requêtes HTTP API (`POST /master/chat`)
```powershell
# Question Fast
curl -X POST http://127.0.0.1:8000/master/chat `
  -H "Content-Type: application/json" `
  -d '{"text": "Quelle est la différence entre un thread et un processus ?", "speed": "fast"}'

# Question Coding
curl -X POST http://127.0.0.1:8000/master/chat `
  -H "Content-Type: application/json" `
  -d '{"text": "Écris un décorateur Python avec gestion des erreurs", "speed": "reasoning"}'
```

### C. Recherche Web & Ingestion d'URLs
- **Recherche Web Souveraine :** `POST /capabilities/web/search` (DuckDuckGo par défaut, Tavily si configuré).
- **Lecture URL Sécurisée (Anti-SSRF) :** `POST /capabilities/web/read` (SafeWebFetcher natif avec filtrage des adresses privées).

### D. Voix & Vision
- **Synthèse Vocale (TTS) :** `POST /perception/tts` (Modèle Kokoro-82M ONNX local à 24kHz).
- **Reconnaissance Vocale (STT) :** `POST /perception/stt` (Nemotron ASR / Whisper ONNX).
- **Vision Multimodale :** `POST /perception/vision` (Gemini Flash Multimodal).

---

## 4. GOUVERNANCE DU FAILOVER ET DU FAST EXIT

Le chemin d'exécution respecte rigoureusement la cascade suivante :

```
Requête Utilisateur
       │
       ▼
1. [ Response Cache ] ──────────────► Hit ? (0.85 ms, 0 quota) ➔ RETOUR IMMÉDIAT
       │ Miss
       ▼
2. [ Singleflight Async ] ──────────► Requête identique en cours ? Coalesce sans doublon
       │ Leader
       ▼
3. [ Gemini Cloud Primary ]
       ├─ Succès 200 OK ────────────► RETOUR & CACHE
       ├─ HTTP 429 Quota ───────────► Rotation sur modèle/projet suivant dans GeminiPool
       └─ Panne Transport (Timeout) ─► FAST EXIT IMMÉDIAT (15s max) ➔ Déclenchement Groq
       │
       ▼
4. [ Groq Cloud Same-Role ]
       ├─ Succès 200 OK ────────────► RETOUR & NOTIFICATION FAILOVER
       └─ Échec (413/429/Timeout) ──► Bascule Ollama
       │
       ▼
5. [ Ollama Local (Dernier Recours) ]
       ├─ Succès 200 OK ────────────► RETOUR
       └─ Défaillance / Offline ────► FAIL_CLOSED Sécurisé (Message clair sans crash)
```

---

## 5. DISTINCTION DES DOMAINES DE QUOTA

1. **Quota Plateforme Antigravity :**
   - Visible uniquement dans l'interface de développement Antigravity.
   - Géré hors bande par Google Deepmind, **strictement indépendant** des APIs d'E-ZzIO.
2. **Quota Runtime Gemini API :**
   - Observable directement par E-ZzIO via les codes de statut HTTP `429` et les en-têtes `Retry-After`.
   - Géré dynamiquement par `gemini_pool` pour délester les projets sans bloquer le serveur.

---

## 6. GUIDE DE GESTION DES INCIDENTS (PLAYBOOK)

| SYMPTÔME | DIAGNOSTIC | ACTION OPÉRATIONNELLE |
|---|---|---|
| **Gemini 429 Quota Exhausted** | Télémétrie indique `GEMINI-POOL: Quota-Exhausted` | Aucune action manuelle requise : `ModelRouter` bascule automatiquement sur `groq/compound` (Same-Role). |
| **Timeout Réseau Cloud (Panne Google)** | Requête prend ~15s au lieu de 600ms | Le **Fast Exit** coupe la tentative Gemini après 15s et sert la réponse via Groq en 3s. |
| **Tous les Clouds Indisponibles** | Métriques affichent `FAIL_CLOSED` | Vérifier la connectivité Internet. Démarrer `ollama run hermes3:8b` si l'inférence locale hors-ligne est souhaitée. |
| **Web HUD Inaccessible** | Port 8000 non joignable | Relancer `python web_server.py`. Vérifier qu'aucun autre processus n'occupe le port 8000. |
| **Discord Bot Déconnecté** | Pas de réponse aux mentions | Vérifier `DISCORD_BOT_TOKEN` dans `secrets/.env` et relancer `python -m core.integrations.discord.discord_client`. |

---

## 7. PROCÉDURE DE RETOUR ARRIÈRE (ROLLBACK)

En cas de régression inattendue sur les fichiers de production :

```powershell
# Vérifier les modifications
git diff

# Restaurer l'état gelé certifié
git checkout core/providers/gemini_provider.py core/cognition/model_router.py
```
