# EVIDENCE RULE — NO CLAIM WITHOUT OBSERVABLE PROOF
**E-ZZIO Standard Constitutionnel de Gouvernance et de Vérité Factuelle**
**Date d'entrée en vigueur :** 30 août 2026

---

## 1. PRINCIPE CARDINAL
```text
NO HASH / NO INSTALL / NO EXECUTION = NO CLAIM OF IMPLEMENTATION
"Autonome dans l'action, extrêmement conservateur dans ses affirmations."
```

Aucun composant, outil ou capacité ne doit être présenté à un niveau supérieur à ce qui est directement observé et prouvé par des éléments reproductibles.

---

## 2. NIVEAUX DE PREUVE STRICTS (TAXONOMIE EXCLUSIVE)

1. **`DOCUMENTED`** : Décrit dans une spécification, une proposition ou un document d'intention. Aucun code ou paquet n'a été vérifié ou déployé.
2. **`DISCOVERED`** : Recensé par un moteur de recherche, un catalogue ou un index technique comme candidat potentiel.
3. **`SOURCE_VERIFIED`** : Référence d'origine (dépôt Git, registre de paquets, URL officielle) vérifiée comme existante et accessible.
4. **`INSTALLED`** : Fichiers physiquement présents sur le disque local avec chemin absolu et empreinte SHA-256 calculée.
5. **`EXECUTED`** : Exécution physique observée en direct avec capture des traces ou sorties brutes (logs, PID, code retour).
6. **`TEST_VERIFIED`** : Validation automatisée via une suite de tests unitaire ou d'intégration exécutée avec succès (`pytest`).
7. **`RUNTIME_VERIFIED`** : Comportement observé et mesuré en conditions réelles de production (ex: requête HTTP sur `web_server.py:8001`).
8. **`PROVEN`** : Ensemble complet et cohérent de preuves reproductibles couvrant précisément l'intégralité de l'affirmation faite (sans extrapolation).
9. **`UNVERIFIED`** : La preuve manque ou est incomplète ; l'absence de certitude est explicitement déclarée.
10. **`FALSE`** : Affirmation antérieure contredite par l'observation directe (ex: cas Chatterbox-Nano).

---

## 3. FICHE MACHINE-READABLE OBLIGATOIRE

Toute mention d'outil ou de capacité dans un rapport doit respecter le format suivant :

```text
TOOL_ID:                <identifiant unique>
SOURCE_URL:              <URL du dépôt/source d'origine>
COMMIT_OR_VERSION:       <hash de commit ou numéro de version exact>
LICENSE_CODE:            <licence du code>
LICENSE_WEIGHTS:         <licence des poids si applicable, ou N/A>
INSTALL_PATH:            <chemin exact sur le disque, ou "NON INSTALLÉ">
FILE_HASHES:             <SHA-256 des fichiers principaux, ou "N/A">
DEPENDENCIES:            <dépendances requises>
HARDWARE_REQUIREMENTS:   <RAM/VRAM/CPU nécessaires et adéquation machine>
INSTALL_STATUS:          <DOCUMENTED | DISCOVERED | SOURCE_VERIFIED | INSTALLED>
EXECUTION_STATUS:        <EXECUTED avec log, ou UNVERIFIED>
TEST_STATUS:             <TEST_VERIFIED avec fichier de test, ou UNVERIFIED>
RUNTIME_STATUS:          <RUNTIME_VERIFIED avec preuve, ou UNVERIFIED>
EVIDENCE_PATHS:          <chemins exacts vers logs/tests/fichiers>
FINAL_CLASSIFICATION:    <un seul des niveaux EVIDENCE RULE, le plus bas justifié>
```

---

## 4. CLAUSE ANTI-OVERCLAIM DE CERTIFICATION

> **Aucun bloc de synthèse ou de certification finale ne peut utiliser les termes `100%`, `PROVEN`, `OPERATIONAL`, `ACTIVE`, `QUALIFIED`, `SOVEREIGN`, `CERTIFIED` sans un renvoi direct et vérifiable vers la fiche machine-readable ou la ligne de `CLAIM_EVIDENCE_MATRIX.md` qui le justifie précisément. Un terme de ce type sans renvoi est automatiquement considéré comme une violation de l'EVIDENCE RULE, à corriger avant la clôture de toute mission.**


