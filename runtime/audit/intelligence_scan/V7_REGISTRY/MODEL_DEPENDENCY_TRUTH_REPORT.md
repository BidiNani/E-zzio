# E-ZZIO V7.22 — Model Dependency Truth Report
**Date de certification :** 2026-08-11T19:49:17Z
**Statut du chemin actif :** SANITIZED (Zéro référence active aux modèles legacy)

## 1. Cartographie de l'Isolation Legacy
| Modèle Legacy | Statut dans le Chemin Actif | Localisation des Traces Historiques | Action de Gouvernance |
| :--- | :--- | :--- | :--- |
| llama3.2:3b | **EXCLUS** | Anciens rapports / backups / tests | Conservation en archive (Bruit forensic) |
| phi4-mini:latest | **EXCLUS** | Anciens catalogues déclaratifs | Isolation stricte |
| qwen2.5-coder:1.5b | **EXCLUS** | Anciens mappings de code | Remplacé par la version 7B |

## 2. Validation du Parc Actif V7.21
Le moteur d'exécution (Dispatcher & Adaptive Governor) ne s'interface qu'exclusivement avec les 6 composants certifiés du fichier model_capabilities.json.
