# E-ZZIO V7.11.5.9 — Decision Governor Surface Report
**Date :** 2026-08-11T17:49:22.116606
**Cible inspectée :** `runtime.recovery.decision.governor.DecisionGovernor`
**Statut :** `SUCCESS`

## 1. Paramètres du Constructeur (`__init__`)
- ` auto_threshold ` (Défaut: `0.9`)
- ` supervised_threshold ` (Défaut: `0.8`)

## 2. Méthodes Publiques et Signatures Exactes
Voici les véritables points d'entrée exposés par le DecisionGovernor :
- `govern(action_type, confidence)`

## 3. Conclusion de l'Inspecteur
Ce rapport lève l'ambiguïté sur la manière d'interagir avec le DecisionGovernor, permettant d'aligner définitivement le harnais de test V7.11.5.x.

**Registre JSON :** `decision_governor_surface.json`