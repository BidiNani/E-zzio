# E-ZZIO V9.0 — SECURITY BOUNDARY & GOVERNANCE

---

## 1. LES 3 NIVEAUX D'AUTORISATION DE `CapabilityPolicy`
1. **`ALLOW`** : Actions passives en lecture seule et sans impact externe (ex: lecture de fichier interne dans le workspace, recherche mémoire FTS5, extraction de métadonnées vidéo).
2. **`REQUIRE_HUMAN`** : Actions actives avec mutation ou appel externe (ex: modification/écriture de fichier, création de commit Git, envoi d'email/Slack, exécution de commande shell).
3. **`DENY`** : Actions proscrites ou destructives (ex: traversée de répertoire hors workspace, tentative d'accès à des IP privées/locales via SSRF, suppression de base mémoire canonique).

---

## 2. ISOLATION DE LA PERCEPTION & DONNÉES NON FIABLES
Toute donnée externe provenant du web, d'un fichier utilisateur, d'un sous-titre YouTube ou d'une réponse SaaS est systématiquement étiquetée :
```text
[DONNÉE PASSIVE NON FIABLE]
```
Elle est traitée comme un objet de données inerte et ne peut en aucun cas être injectée directement en tant qu'instruction système dans le prompt d'un modèle sans assainissement.

---

## 3. CONFINEMENT SYSTÈME & DISQUE
- **Anti-SSRF (`SafeFetcher`)** : Résolution DNS stricte et interdiction formelle de connexion vers `127.0.0.1`, `localhost`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254`.
- **Confinement Disque (`Path Confinement`)** : Vérification stricte que tout chemin cible est enfant du workspace autorisé via `os.path.commonpath`.
