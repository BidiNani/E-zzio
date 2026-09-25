# ADR — Contrat canonique de `force_cloud`

**Date** : 2026-09-24
**Status** : ACCEPTED
**Repository** : `G:\AI\E-zzio`
**HEAD au moment de la décision** : `46f5c9b3da49fb29e3a9d27a1784fc13d06db9cf`

---

## Décision

`force_cloud=True` constitue une **contrainte d'exécution** garantissant qu'une requête
ne soit pas exécutée par un provider local.

---

## Règles contractuelles

### Règle 1 — Route nominale déjà cloud

Lorsque la route nominale sélectionnée par `ModelRouter` est déjà un provider cloud,
aucun remplacement de modèle ou de provider n'est effectué.

### Règle 2 — Route nominale locale → recherche canonique

Lorsque la route nominale est locale (ex. `ollama`), le système doit rechercher une
**cible cloud explicitement canonique pour le rôle ou le profil demandé**.

La résolution doit passer par `CanonicalModelRegistry` / `ROLE_MAP`.

Une transformation implicite vers un rôle ou modèle différent du rôle original
**n'est pas autorisée**.

### Règle 3 — Absence d'équivalent cloud → fail-closed

Lorsqu'aucune cible cloud canonique n'existe pour le rôle demandé,
l'exécution doit échouer de manière **fail-closed** (lever `RouteIntegrityError`)
plutôt que de substituer silencieusement un autre rôle ou modèle.

### Règle 4 — `gemini-3.7-flash` n'est pas le contrat

Le modèle `gemini-3.7-flash` ne constitue pas, à lui seul, le contrat de `force_cloud`.
Son usage historique (commit `3fcf7632`) était opportuniste (seul provider cloud
disponible à ce moment), non contractuel.

---

## Contexte

### Implémentation certifiée (conforme au contrat)

```python
# core/agent/agent_provider.py — lignes 84-94
if force_cloud and provider_name == "ollama":
    cloud_rec = canonical_model_registry.resolve_cloud_role(original_role)
    if cloud_rec is None or not cloud_rec.provider or cloud_rec.provider == "ollama":
        raise RouteIntegrityError(
            f"[FAIL-CLOSED] force_cloud requested but no canonical cloud route exists "
            f"for role={original_role!r} "
            f"(nominal provider={provider_name!r}, model={selected_model!r})"
        )
    provider_name = cloud_rec.provider
    selected_model = cloud_rec.name
```

---

## Autorité

L'autorité de résolution du modèle cloud équivalent est :

```python
CanonicalModelRegistry.resolve_cloud_role(original_role)
  → si 1 candidat cloud unique pour original_role → modèle cloud canonique
  → si 0 candidat ou >1 candidats (ambiguïté) → None → RouteIntegrityError (fail-closed)
```

`ModelRouter` reste l'autorité de sélection nominale.
`AgentProviderAdapter` applique uniquement la contrainte de canal (cloud/local).
Aucune autorité autonome de sélection de modèle dans l'Adapter.

---

## État de l'implémentation

L'implémentation est certifiée et conforme aux 4 règles contractuelles :
- `CanonicalModelRegistry.resolve_cloud_role()` résout dynamiquement le record sans hardcode.
- Les tests unitaires et d'intégration couvrent la résolution exacte, l'absence de candidat et l'ambiguïté.
