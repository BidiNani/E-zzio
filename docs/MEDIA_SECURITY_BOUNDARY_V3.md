# E-ZZIO V10.0 — MEDIA SECURITY BOUNDARY SPECIFICATION V3

---

## 1. RÈGLES DE CONFINEMENT ET DE SÉCURITÉ
1. **Isolation Subprocess :** Tout processus externe lancé par E-ZzIO est borné par un timeout strict (ex. 60s pour l'édition d'image, 180s pour la vidéo), avec destruction automatique (`kill()`) en cas de dépassement.
2. **Scrubbing de Secrets :** Les variables d'environnement confidentielles (`.env`, `SECRETS_VAULT`, clés privées) ne sont jamais transmises aux sous-processus multimédias.
3. **Contrôle d'Autorité :** Les opérations de mutation/écriture passent obligatoirement par `CapabilityPolicy.evaluate_scope()` avec la décision `REQUIRE_HUMAN`.
