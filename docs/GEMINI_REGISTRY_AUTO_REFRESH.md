# E-ZZIO — GEMINI REGISTRY AUTO-REFRESH

> **Status** : OPERATIONAL — CERTIFIED — SINGLE-PROCESS  
> **Date** : 2026-09-01  
> **Certification** : CERTIFIED WITH WARNINGS (warnings : CANDIDATE models retained indefinitely — accepted policy)  
> **Tests baseline** : 17/17 PASS

---

## 1. Vue d'ensemble

Le mécanisme de synchronisation automatique du registre Gemini connecte la découverte réelle de l'API Google Gemini au registre opérationnel persistant (`data/models/registry.json`), via trois déclencheurs : démarrage, déclenchement manuel, et scheduler quotidien.

Ce mécanisme est un **inventaire dynamique**, pas un mécanisme d'activation. Il ne modifie jamais le routage de production.

```
Google Gemini API
      ↓
GeminiDiscovery
      ↓
registry_refresh.py  →  refresh_gemini_registry_async()
      ↓
ModelLifecycleManager
      ↓
ModelRegistry.save()  (atomic: tempfile + os.replace)
      ↓
data/models/registry.json
      ↓
state/audit/discovery/gemini_YYYY-MM-DD.json
```

---

## 2. Composants

| Fichier | Rôle |
|---|---|
| `core/models/registry_refresh.py` | Pipeline de synchronisation. Point d'entrée : `refresh_gemini_registry_async()` |
| `core/models/registry_refresh_service.py` | Service applicatif. Gère startup, manuel, scheduler quotidien et lock de concurrence |
| `routers/registry.py` | Router FastAPI — expose `POST /api/models/registry/refresh/gemini` |
| `core/models/discovery/gemini.py` | `GeminiDiscovery.discover()` — appel API Google, filtrage, normalisation |
| `core/models/lifecycle.py` | `ModelLifecycleManager.ingest_discovery()` — transitions d'état |
| `core/models/registry.py` | `ModelRegistry` — persistance atomique JSON |
| `data/models/registry.json` | Registre opérationnel (source de vérité persistante) |
| `state/audit/discovery/` | Audits forensic par date |

---

## 3. Déclencheurs

### 3.1 Démarrage (STARTUP)

```
web_server.py — lifespan()
      ↓
load_secrets()           ← autorité unique des secrets
      ↓
memory_gateway.init()
      ↓
GeminiRegistryRefreshService.startup()
      ↓
refresh_gemini_registry_async()
      ↓ succès              ↓ échec
   audit écrit           WARNING loggué
      ↓                      ↓
      └──────────┬───────────┘
                 ↓
          asyncio.create_task()  ← scheduler quotidien lancé
                 ↓
          E-ZzIO READY
```

**CRITIQUE** : une panne de l'API Google au démarrage n'empêche jamais E-ZzIO de démarrer. `startup()` intercepte toute exception et retourne `status=failure` sans re-raise.

### 3.2 Déclenchement manuel (MANUAL)

```
POST /api/models/registry/refresh/gemini
      ↓
GeminiRegistryRefreshService.trigger()
      ↓ lock libre         ↓ lock occupé
refresh_gemini_registry_async()   status=skipped
      ↓
Réponse HTTP (secret-safe)
```

Champs retournés : `status`, `provider`, `discovered_count`, `new_count`, `superseded_count`, `registry_count`, `timestamp`, `stats`.  
Champs **jamais** retournés : API key, credential, token, secret.

### 3.3 Scheduler quotidien (DAILY)

```
asyncio.create_task(_scheduler_loop)   ← lancé une seule fois dans startup()
      ↓
asyncio.sleep(86 400s)
      ↓
tick : refresh_gemini_registry_async()
      ↓ succès         ↓ échec
   audit écrit      WARNING loggué
      ↓                  ↓
      └────────┬──────────┘
               ↓
      asyncio.sleep(86 400s)  ← boucle continue quoi qu'il arrive
```

**CRITIQUE** : une exception dans un refresh ne tue pas la boucle. Le scheduler survit à toute erreur individuelle.

---

## 4. Politique de lifecycle des modèles

```
Nouveau modèle découvert par l'API
            ↓
        CANDIDATE          ← toujours, jamais ACTIVE
            ↓
    conservé indéfiniment

Modèle absent de l'API suivante
            ↓
    CANDIDATE conservé     ← aucune suppression physique, aucune transition forcée
    (ACCEPTED OPERATIONAL POLICY)

Modèle ACTIVE absent de l'API
            ↓
    QUARANTINED            ← seule transition légale via lifecycle_manager
```

**Invariant** : `refresh_gemini_registry()` ne contient aucun appel à `activate()`, `promote()`, `enable_for_routing()`, ou `set_active()`.

---

## 5. Politique fail-safe

```
Google API unavailable
Timeout (> 15s)
HTTP 429
HTTP 503
Network failure
Invalid payload
Unexpected exception
        ↓
refresh failure
        ↓
WARNING loggué (aucun secret dans le log)
        ↓
registry.json INCHANGÉ (écriture atomique non déclenchée)
        ↓
E-ZzIO continue normalement
        ↓
prochaines exécutions du scheduler restent actives
```

---

## 6. Politique d'audit

- **Succès** → `state/audit/discovery/gemini_YYYY-MM-DD.json` écrit.
- **Échec** → WARNING loggué, aucun audit écrit.
- **Filtrage** : tout champ dont le nom contient `key`, `secret`, `token`, `credential`, `password` est exclu du JSON d'audit.

---

## 7. Invariant de concurrence — SINGLE-PROCESS

### Mode de déploiement actuel

```
uvicorn web_server:app  (sans --workers N)
= SINGLE-PROCESS
```

Le `asyncio.Lock` dans `GeminiRegistryRefreshService._do_refresh()` protège contre la concurrence interne à l'unique processus :

```
1 worker  →  1 event loop  →  1 scheduler  →  SAFE
```

### Restriction obligatoire

> **E-ZzIO MUST REMAIN SINGLE-PROCESS  
> WHILE THE INTERNAL DAILY GEMINI SCHEDULER  
> USES asyncio.create_task() + asyncio.Lock.**

> **DO NOT ENABLE MULTIPLE UVICORN WORKERS  
> WITHOUT FIRST REPLACING THE INTERNAL  
> SCHEDULER WITH A PROCESS-SAFE MECHANISM.**

Le `asyncio.Lock` n'est **pas** un lock inter-processus. En mode multi-worker :

```
N workers  →  N event loops  →  N schedulers  →  NOT SAFE
(refresh concurrent inter-process, écritures registry.json concurrentes)
```

### Migration future (FUTURE ARCHITECTURAL TASK — non implémentée)

| Option | Description |
|---|---|
| **A** | Scheduler OS externe (cron / Task Scheduler) appelant `POST /api/models/registry/refresh/gemini` sur un seul worker désigné |
| **B** | Lock fichier process-safe (`fcntl.flock` Linux / `msvcrt.locking` Windows) autour du refresh |
| **C** | Service scheduler dédié (processus séparé) |
| **D** | Lock distribué / scheduler centralisé (Redis, Zookeeper) |

**Aucune option n'est choisie ni implémentée dans cette version. Ce choix est délibéré.**

---

## 8. Fichiers protégés (FROZEN — DO NOT MODIFY WITHOUT GATE)

Les fichiers suivants sont protégés au niveau du mécanisme auto-refresh. Toute évolution de leur rôle architectural nécessite une nouvelle validation explicite (Gate d'Architecture).

| Fichier | Rôle protégé |
|---|---|
| `core/models/gemini_pool.py` | Infrastructure multi-clés Gemini — frozen |
| `core/cognition/model_router.py` | Autorité de routage — frozen |
| `core/models/lifecycle.py` | State machine lifecycle — contrat figé |
| `core/models/discovery/gemini.py` | Filtrage et normalisation discovery — contrat figé |
| `core/models/registry_refresh.py` | Pipeline de synchronisation — contrat figé |

**Rappel de séparation des responsabilités :**

```
Registry refresh  ≠  Model activation  ≠  Model routing
```

Ces trois couches sont indépendantes et doivent le rester.

---

## 9. Invariants de production

| Invariant | Valeur |
|---|---|
| ModelRouter | FROZEN — aucune modification |
| Routing policy | FROZEN — aucune modification |
| Fallback policy | FROZEN — aucune modification |
| `gemini_pool.py` | FROZEN — aucune modification |
| Activation automatique | FORBIDDEN |
| Suppression physique du registre | FORBIDDEN |
| Secrets dans les logs | FORBIDDEN |
| Secrets dans les audits | FORBIDDEN |
| Secrets dans les réponses HTTP | FORBIDDEN |
| Pruning automatique des CANDIDATE | NOT IMPLEMENTED — ACCEPTED |

---

## 10. Baseline de tests (2026-09-01)

| Suite | Résultat |
|---|---|
| `tests/test_registry_refresh.py` | 7/7 PASS |
| `tests/test_registry_auto_refresh.py` | 10/10 PASS |
| **Total** | **17/17 PASS** |

Tests couverts :

1. Startup success
2. Startup failure resilience (Google API indisponible → E-ZzIO continue)
3. Manual trigger
4. Daily scheduler (tick simulé)
5. Scheduler resilience (échec #1 → exécution #2 normale)
6. Concurrent refresh (lock — skipped)
7. No auto-activation
8. Routing isolation (gemini_pool non modifié)
9. Secret safety (réponse trigger)
10. Secret safety (startup failure)

---

## 11. État du registre au 2026-09-01

```
Total entrées Gemini :  38
Lifecycle :             38 × CANDIDATE
ACTIVE :                0
Audit :                 state/audit/discovery/gemini_2026-09-01.json
```
