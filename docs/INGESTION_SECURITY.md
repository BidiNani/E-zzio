# E-ZZIO V10.0 — INGESTION SECURITY SPECIFICATION

---

## 1. GOUVERNANCE CONTRE LES VECTEURS D'ATTAQUE DE FICHIERS
- **Anti-Executable Disguise** : Détection binaire immédiate des en-têtes PE Windows (`MZ`) et ELF (`\x7fELF`) camouflés sous de fausses extensions (.txt, .png, .pdf) ➔ Statut `BLOCKED_EXECUTABLE`.
- **Anti-Zip-Slip** : Élimination stricte des chemins contenant `..` ou démarrant par `/` ou `\\` dans les archives décompressées.
- **Anti-Zip-Bomb** : Plafond strict à 50 fichiers et 100 Mo décompressés maximum.
- **Taille Maximale de Fichier** : 50 Mo par défaut.
- **Tag de Provenance Immuable** : `[DONNÉE PASSIVE NON FIABLE]` injecté systématiquement dans toute donnée extraite.
