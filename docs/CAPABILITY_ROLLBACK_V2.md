# E-ZZIO V10.0 — CAPABILITY ROLLBACK & SELF-HEALING V2

---

## 1. PROCÉDURE DE ROLLBACK
- **Déclenchement :** Anomalie de santé, régression unitaire ou comportement non conforme.
- **Actions :**
  1. Bascule immédiate du statut vers `QUARANTINED`.
  2. Écriture du flag `healthy = false` dans `capability.manifest.json`.
  3. Notification à l'`AuditLedger`.
  4. Redirection automatique vers un backend alternatif sans impact sur le Core.
