# E-ZZIO V10.0 — CAPABILITY TRUST MODEL V2

---

## 1. LES NIVEAUX DE CONFIANCE (TRUST LEVELS)

| Niveau | Nom | Définition | Action Autorisée |
| :---: | :--- | :--- | :--- |
| **`TRUST_0`** | `UNKNOWN` | Source inconnue / non qualifiée | **Exécution STRICTEMENT INTERDITE** |
| **`TRUST_1`** | `DISCOVERED` | Identifié via recherche GitHub/Docs | Analyse passive uniquement |
| **`TRUST_2`** | `SANDBOXED` | Déployé dans `G:\AI\external\capabilities\` | Tests et benchmarks isolés |
| **`TRUST_3`** | `QUALIFIED` | Tests unitaires & santé validés | Intégration dans le catalogue |
| **`TRUST_4`** | `ACTIVE` | Opérationnel sous `CapabilityPolicy` | Exécution de tâches utilisateur |
