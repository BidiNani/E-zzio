# Manifeste Architectural d'E-ZzIO (V9.0)
## *Local-First Cognitive Operating System*

> **Vision Fondamentale** : E-ZzIO n'est ni un wrapper d'API, ni un simple agent LLM. C'est un **système d'exploitation cognitif personnel et souverain**, auto-hébergé, conçu pour orchestrer de l'intelligence artificielle, des outils locaux et des services distants sous contrôle humain strict, conçu pour minimiser les coûts logiciels et privilégier les capacités gratuites/locales, avec une absence de dépendance critique envers un fournisseur unique.

---

## 🏛️ 1. Le Changement de Paradigme : L'Autorité reste E-ZzIO

Les modèles, moteurs de recherche et connecteurs SaaS sont des **composants interchangeables**. L'autorité, la sécurité et la mémoire résident exclusivement dans le noyau souverain E-ZzIO.

```
                    E-ZZIO (Autorité Centrale)
                               │
                        ┌──────┴──────┐
                        │   Runtime   │
                        │  Authority  │
                        └──────┬──────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
          Cognition         Governance      Capabilities
              │                │                │
         Gemini/Ollama     Policy/Audit     Web/SaaS/Files
              │                │                │
              └────────────────┼────────────────┘
                               │
                            Memory
                               │
                          Perception
                               │
                        Monde Extérieur
```

---

## 📐 2. La Tripartition Architecturale Stricte

Pour empêcher toute complexification incontrôlée et garantir qu'aucune technologie externe ne devienne une autorité occulte :

```
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ 1. 🏛️ CANONIQUE (Autorité E-ZzIO — Noyau Non Négociable)                               │
 │    • Point d'entrée serveur unique : web_server.py:8001                               │
 │    • Runtime & Dispatcher central : core.sdk.ezzio                                    │
 │    • Arbitre de sécurité : CapabilityPolicy (ALLOW / REQUIRE_HUMAN / DENY)            │
 │    • Journal d'audit immuable : AuditLedger (Chaînage cryptographique SHA-256)        │
 │    • Mémoire multi-niveaux : MultiTierMemory (L0 à L5, SQLite WAL + FTS5)             │
 │    • Sauvegarde & Résilience : BackupEngine CAS (Déduplication 100% fichiers par SHA)  │
 │    • Coffre-fort des secrets : SecretsVault (AES-256-GCM / PBKDF2 / DPAPI Windows)    │
 ├────────────────────────────────────────────────────────────────────────────────────────┤
 │ 2. ⚙️ CAPABILITY (Capacités Qualifiées — Interchangeables & Contractualisées)          │
 │    • Cognition : Ollama local (Qwen2.5-Coder) / Pool Gemini Cloud (3.7 / 3.5 Flash)    │
 │    • Recherche & Extraction Web : DuckDuckGo HTML / SearXNG local / Crawl4AI Engine    │
 │    • SaaS Directs (Zéro Tiers) : GitHub REST Direct / Google Workspace / Slack Direct │
 │    • Génération Graphique : Pillow (procédural local <30ms) / Gemini Image Cloud       │
 │    • Perception Déterministe : RSSAdapter (RSS 2.0 / Atom 1.0 avec filtre SSRF)       │
 ├────────────────────────────────────────────────────────────────────────────────────────┤
 │ 3. 🧪 EXPÉRIMENTAL (Sas de Qualification — Strictement Hors Chemin Critique)          │
 │    • Candidats LLM : glm-5.3-candidate (Fail-Closed en production)                    │
 │    • Candidats Extraction / Voix : Docling, Piper TTS                                  │
 │    • Toute nouvelle intégration non certifiée par tests d'usage réel                   │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ 3. Les 4 Règles Inviolables du Runtime

### Règle 1 : La Frontière de Perception Non Négociable
Toute donnée provenant du monde extérieur (pages web, flux RSS, emails, messages Slack, retours d'API) est considérée comme **donnée passive non fiable** :
$$\text{Monde Extérieur} \longrightarrow \text{Perception (Filtre SSRF)} \longrightarrow \text{Normalisation Markdown/Texte} \longrightarrow \text{[Donnée Passive Non Fiable]} \longrightarrow \text{Cognition}$$

### Règle 2 : Le Failover Piloté Exclusivement par le Runtime
Le basculement entre Cloud (Gemini Pool) et Local (Ollama) n'est **jamais piloté par le modèle ni par un connecteur**, mais par l'arbitre central du **Runtime**. Si une erreur 429 ou coupure réseau survient, le Runtime redirige la requête vers le moteur local en mode **Fail-Closed**.

### Règle 3 : La Gouvernance Tri-Partite
Aucun appel d'outil ou action d'agent ne peut court-circuiter la `CapabilityPolicy` :
- **`ALLOW`** : Actions de lecture et d'analyse passive (recherche web, lecture dépôt, parse RSS).
- **`REQUIRE_HUMAN`** : Actions mutantes ou à impact externe (envoi d'email, publication Slack, écriture GitHub, modifications système).
- **`DENY`** : Actions destructives hors périmètre ou tentatives d'atteinte SSRF.

### Règle 4 : La Minimisation et le Cloisonnement des Données Sortantes
Le système est conçu pour minimiser et contrôler les flux de données sortants par :
- Un confinement strict du système de fichiers (`os.path.commonpath`).
- L'utilisation de connecteurs directs auto-hébergés sans agrégateurs tiers.
- Le déchiffrement direct en RAM des secrets via la DPAPI Windows ou variable d'environnement système.

---

## 🧪 4. Métrologie & Référentiel de Certification

L'état opérationnel et la conformité du noyau sont attestés par l'exécution complète de la suite de tests :
- **89 fichiers de tests**
- **270 items collectés**
- **270 passed (100% de succès)**
- **0 failed, 0 skipped**
- **Temps d'exécution moyen** : ~60 secondes sur CPU local.
