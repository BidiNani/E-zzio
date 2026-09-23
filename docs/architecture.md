# Architecture E-ZZIO - Etat reel au 23/09/2026

> **Note importante** : ce document decrit **l'etat reel du code**, pas la vision cible.
> Il a ete genere apres inspection directe du depot et corrige plusieurs formulations
> trop absolues de la fiche descriptive initiale.

---

## 1. Chemin d'execution reel

### 1.1 Pipeline actuel

```
EzzioMaster.execute_intent()
    |
    v
ModelRouter.select_engine()  (selection du modele)
    |
    v
_detect_provider_from_model()  (detection du provider)
    |
    v
Provider.generate()  (appel direct)
    |
    v
fallback Gemini si echec
```

### 1.2 Ce qui a change par rapport a la vision initiale

La fiche descriptive initiale annoncait :

```
Master -> Federation -> Router -> Provider
```

**Le code reel** est plus simple :

```
EzzioMaster -> ModelRouter -> Provider -> fallback
```

`core/agent/coder_federation.py` existe toujours mais fonctionne comme **gateway
de compatibilite** qui delegue a `ezzio_master.execute_intent()`. Il n'est plus
l'autorite d'execution active.

### 1.3 Tension architecturale detectee

**Observation** : `CanonicalIdentity.policy["execution_authority"]` declare
`core/agent/coder_federation.py` comme autorite d'execution.

**Mais** : `EzzioMaster` instancie `NativeHarness` avec :
- `router=None`
- `policy_guard=None`
- `audit_ledger=None`

**Statut** : `[OBSERVED]` tension d'architecture / autorite a auditer.

**Ce n'est PAS un bug confirme.** Il faut analyser tous les appelants et contrats
de `NativeHarness`, `ModelRouter`, `coder_federation` et les routes avant de conclure
a un bypass fonctionnel.

---

## 2. Mode cloud-first vs local-first

### 2.1 Etat actuel

`core/ezzio_master.py` contient :

```python
force_cloud: bool = False  # hybride : cloud-first + fallback local
# Hybride : cloud-first avec fallback local automatique si pas d'Internet.
```

**Le comportement par defaut est hybride : cloud-first avec fallback local automatique.**

### 2.2 Tableau des occurrences

| Fichier | Ligne | Valeur par defaut |
|---|---|---|
| `core/ezzio_master.py` | 198 | `False` (hybride) |
| `core/sdk.py` | 44 | `False` (hybride) |
| `core/agent/agent_provider.py` | 109 | `False` |
| `core/cognition/cognitive_gateway.py` | 122 | `False` (depuis constraints) |
| `core/integrations/discord/discord_client.py` | 417 | `False` (hybride) |

**Le chemin principal (Master, SDK, Discord) est hybride : cloud-first avec fallback local automatique.**

---

## 3. Registry canonique des modeles

### 3.1 Etat reel

`core/routing/registry.py` declare :

```python
ProviderName = Literal["gemini", "groq", "anthropic", "openai", "mistral"]
```

**Registry canonique** : Gemini, Groq, Anthropic, OpenAI, Mistral.

### 3.2 Providers hors registry canonique

Ces providers sont utilises a l'execution mais **ne sont pas dans le type canonique** :
- **OpenRouter** : detecte par `/` dans le nom du modele
- **NVIDIA** : detecte par `nvidia/` ou `nvapi`
- **Ollama** : detecte par `:` ou `:latest`

Voir `_detect_provider_from_model()` dans `core/ezzio_master.py` L103-129.

### 3.3 Correction de la fiche

La formulation initiale "registre canonique de 5 providers
Groq/Gemini/OpenRouter/NVIDIA/Ollama" n'est **pas exacte**.

Le registry canonique contient **Gemini, Groq, Anthropic, OpenAI, Mistral**.

---

## 4. Composants reellement implementes

### 4.1 Confirme present dans le code

| Composant | Fichier | Statut |
|---|---|---|
| Identite canonique | `core/identity/canonical_identity.py` | Reel (hash SHA-256 verifie) |
| Memoire FTS5 | `core/memory/unified_memory_gateway.py` | Reel (SQLite WAL + FTS5 + BM25) |
| Policy de codage | `core/coding/policy.py` | Reel (whitelist + modes) |
| Bridge d'outils | `core/coding/bridge.py` | Reel (whitelist + confinement + timeout) |
| Coder Worker | `core/coding/coder_worker.py` | Reel (PLAN -> BUILD -> VERIFY, iter <= 3) |
| Evidence Store | `core/security/evidence_store.py` | Reel |
| Immutable Audit Ledger | `core/security/immutable_audit.py` | Reel (hash-chain) |
| State machine tasks | `core/tasks/models.py` | Reel (DRAFT -> ... -> COMPLETED) |
| Model Router | `core/routing/model_router.py` | Reel |
| Canonical Model Registry | `core/routing/registry.py` | Reel (5 providers) |

### 4.2 Precisions importantes

**Audit hash-chain** : rend la falsification **detectable**, mais n'empeche pas
a lui seul la suppression ou le remplacement du fichier de journal. Formulation
correcte : "audit chaine et tamper-evident", pas "infalsifiable".

**Souverainete locale** : le chemin d'execution par defaut passe par des providers
cloud. Formulation correcte : "local-first en option", pas "100% local".

**0 regression** : non verifiable depuis le depot seul. Necessite l'execution
de la suite complete dans un environnement approprie.

---

## 5. Positionnement reel vs concurrents

### 5.1 E-ZZIO = kernel agentique gouverne

```
             E-ZZIO
                |
     +----------+----------+
     |                     |
Gouvernance             Capacites
     |                     |
Identity               LLM providers
Policy                 Coding
Routing                Memory
Evidence               Media
Audit                  Tools
State machine          Search
```

**E-ZZIO n'est pas** "un autre agent autonome". C'est un **kernel agentique
gouverne** qui place la gouvernance, la preuve et l'audit au centre.

### 5.2 Comparaison factuelle

| Domaine | E-ZZIO | OpenMausBot | OpenMuse |
|---|---|---|---|
| Kernel souverain | Oui | Non (harness/app) | Non (agent-computer) |
| Identite canonique | Oui | Par bot | Par session |
| FTS5 | Oui | Non central | Non central |
| Registry modeles | Oui (5 canoniques) | Oui (engine/bot) | Depend harness |
| Router metier | Oui | Autre abstraction | Moins central |
| Coder Worker | Oui | Agents de code | Possible via agent |
| State machine | Oui | Taches/routines | Oui |
| Evidence Store | Oui | Receipts/logs | Action receipts |
| Hash-chain audit | Oui | Non equivalent | Non equivalent |
| Shell controle | Oui | Oui | Oui |
| Browser automation | Limitee | Forte | Tres forte |
| Computer-use | Partielle | Forte | Tres forte |
| Android | A developper | Produit existant | Produit existant |
| GUI desktop | Limitee | Forte | Web/mobile |
| Multimedia specialise | Oui | Secondaire | Secondaire |
| Local LLM | Oui (option) | Oui | Oui selon config |
| Windows native | Oui | Oui | Pas son axe |

---

## 6. Actions recommandees

### 6.1 Court terme

1. **Auditer la tension architecturale** : `execution_authority` vs `NativeHarness`
2. **Decider sur `force_cloud`** : cloud-first ou local-first par defaut
3. **Aligner la fiche descriptive** avec l'etat reel du code
4. **Documenter dans METHOD.md** : architecture reelle, registry canonique reel

### 6.2 Moyen terme

1. **Unifier le chemin d'execution** : clarifier le role de `coder_federation.py`
2. **Corriger `NativeHarness`** : instancier avec les vraies dependances
3. **Renforcer l'audit** : rendre le fichier de log append-only au niveau OS
4. **Completer Browser/Computer-use** : combler l'ecart avec OpenMausBot/OpenMuse

### 6.3 Long terme

1. **Consolider le positionnement** : kernel gouverne vs agent autonome
2. **Publier des benchmarks** : performances reelles, latence, qualite
3. **Documenter les cas d'usage** : qui utilise E-ZZIO et pourquoi

---

## 7. Methodologie de ce document

Ce document a ete genere apres :
1. Inspection directe du depot `BidiNani/E-zzio` (commit `5577f76`)
2. Lecture de `core/ezzio_master.py`, `core/agent/coder_federation.py`,
   `core/routing/registry.py`
3. Grep cible sur `NativeHarness`, `execution_authority`, `force_cloud`
4. Comparaison avec la fiche descriptive initiale

**Principe** : decrire ce qui est, pas ce qu'on voudrait qui soit.

---

*Derniere mise a jour : 23/09/2026*
