# E-ZZIO V10.0 — CAPABILITY SECURITY BOUNDARY SPECIFICATION V1

---

## 1. FRONTIÈRE DE SÉCURITÉ ABSOLUE DU CORE
Toute capacité externe ou serveur MCP hébergé dans `G:\AI\external\` :
1. **N'a aucune autorité cognitive** : Ne peut pas court-circuiter le `CognitiveGateway` ou le `ModelRouter`.
2. **N'a aucun accès aux secrets** : Les clés privées et fichiers `.env` sont scrubbés avant tout appel de sous-processus.
3. **N'a aucun accès arbitraire au shell** : Les exécutions de commandes sont confinées à des briques isolées protégées par timeout.
4. **Ne modifie jamais le code Core** : Tout appel tentant d'altérer `core/` déclenche une alerte de sécurité et une mise en quarantaine (`QUARANTINED`).
