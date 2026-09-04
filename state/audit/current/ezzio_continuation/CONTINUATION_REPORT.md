# 🏛️ E-ZZIO — RAPPORT GLOBAL DE REPRISE ET FEUILLE DE ROUTE

**Date :** 31 août 2026  
**Standard :** `EVIDENCE RULE v1.1`  
**Dépôt :** `G:\AI\E-zzio`

---

## 1. CONTEXTE ARCHITECTURAL VERROUILLÉ

L'état souverain d'E-ZzIO est stabilisé sur les bases formelles suivantes :
- **Autorité Unique de Routage :** `core/cognition/model_router.py` (Cloud-First Gemini Pool, fallback Ollama).
- **Autorité Unique de Mémoire :** `core/memory/unified_gateway.py` (UnifiedMemoryGateway sur SQLite WAL + FTS5).
- **Autorité Unique de Sécurité :** `core/security/secrets_vault.py` (SecretsVault avec déchiffrement mémoire vive).
- **Discord Opérationnel :** Mode conversationnel naturel dans le BUS et commandes slash stabilisées.
- **Ressources Locales Physiques :** 6 modèles Ollama opérationnels (`phi4-mini`, `nemotron-3-nano`, `hermes3`, `qwen3.5`, `nomic-embed-text`, `bge-m3`).
- **Atelier Multi-Agent :** Optimisé en mode *Command-First* (zéro impact sur la production).

---

## 2. RÉCONCILIATION DES FINDINGS DU REGISTRE

| FINDING | SOURCE | NATURE DE L'ÉCART | IMPACT SUR LA PRODUCTION | PLAN DE TRAITEMENT SÛR |
|---|---|---|---|---|
| **ROUTING_DIVERGENCES** | `runtime/model_router/config.json` | Référence d'anciens modèles non installés (`granite4.1`, `qwen3-coder:30b`) | **CONFINÉ SANS IMPACT** (`core/cognition/model_router.py` est l'autorité souveraine) | Aligner `config.json` sur les modèles physiques réels (`phi4-mini`, `hermes3`, `qwen3.5`). |
| **STALE_REFERENCES** | `core/cognition/model_router.py:32` | `LOCAL_FALLBACK_MODEL = 'qwen2.5-coder:7b'` | **POTENTIEL SI REPLI DÉCLENCHÉ** | Proposer la bascule vers `phi4-mini:latest` (validé meilleur fast local). |
| **FORGOTTEN_CAPABILITIES** | Réfutations historiques | Annonces sans code (Firecrawl, Crawl4AI, Chatterbox) | **NUL** (Documenté dans `KNOWN_FALSE_CLAIMS.md`) | Conserver en archive d'audit sans code mort. |
| **UNVERIFIED_ITEMS** | `CREDENTIALS_INVENTORY.json` | 24 variables dormantes | **NUL** (Garde fail-closed active) | Activer les connecteurs au cas par cas lors de l'apport de clés. |

---

## 3. FEUILLE DE ROUTE D'INTÉGRATION TECHNIQUE

### A. Capacité Web Hybride Souveraine
Intégration d'une capacité web à 3 étages sans dépendance lourde :
1. **Étage 1 (Recherche) :** Connecteur Wikipedia interne + Tavily API (quand clé fournie).
2. **Étage 2 (Lecture / Extraction) :** `safe_fetcher.py` local + Jina Reader (quand clé fournie).
3. **Étage 3 (Analyse documentaire) :** `UniversalFileReader` natif (PDF, DOCX, XLSX, HTML).

### B. Architecture du Failover Multi-Provider (Sous l'Autorité Unique de ModelRouter)
```
                     Interface (Discord / CLI / Web HUD)
                                    │
                                    ▼
                             CognitiveGateway
                                    │
                                    ▼
                         [ ModelRouter SOUVERAIN ]
                                    │
                 ┌──────────────────┴──────────────────┐
                 ▼                                     ▼
        (Primary Cloud Target)               (Repli Local Souverain)
         Gemini Project Slot A                   Ollama Local Engine
                 │                                (phi4-mini / hermes3)
        [ Erreur 429 / 5xx ]                           ▲
                 │                                     │
                 ▼                                     │
        (Rotation Cloud de Secours) ───────────────────┘
         Gemini Project Slot B/C      (Si tout le cloud est indisponible)
```

### C. Cache de Réponses LLM d'Atelier
- Clé composite déterministe basée sur `sha256(prompt + context + model + system + toolset + repo_rev)`.
- Stockage technique isolé sans création de seconde mémoire cognitive.

### D. Rôles Dédiés des Modèles Locaux Ollama
- **`phi4-mini:latest` :** FAST_LOCAL & TRIAGE_LOCAL (latence ultra-courte, triage, logique rapide).
- **`nemotron-3-nano:4b` :** TOOLS_LOCAL & GUARDRAIL_LOCAL (validation de schémas et sécurité).
- **`hermes3:8b` :** GENERAL_LOCAL & CONVERSATION_LOCAL (rédaction en français, synthèse narrative).
- **`qwen3.5:9b` :** STRUCTURED_LOCAL (raisonnement lourd local et extraction structurée).

---

## 4. PROCHAINE ACTION À PLUS HAUTE VALEUR

**Action prioritaire recommandée :**
Aligner la configuration locale `runtime/model_router/config.json` et la référence de repli de `core/cognition/model_router.py` sur les modèles réellement installés (`phi4-mini:latest` pour le fast/fallback local et `hermes3:8b` pour le général local), avec validation immédiate par tests ciblés.
