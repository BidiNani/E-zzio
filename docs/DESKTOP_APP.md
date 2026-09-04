# E-ZZIO V9.0 — DESKTOP APPLICATION GUIDE

## 1. DÉMARRAGE RAPIDE

Pour lancer l'application Desktop autonome sur Windows :

```powershell
.\tools\launch_desktop.ps1
```

Le script exécute les opérations suivantes :
1. Vérification de l'environnement virtuel Python (`.venv\Scripts\python.exe`).
2. Démarrage transparent du serveur souverain sur le port 8001 (`uvicorn web_server:app`).
3. Ouverture d'une fenêtre applicative native WebView2 / Edge App autonome (sans barre d'adresse du navigateur) en résolution `1600x1000`.

---

## 2. MODES DE FONCTIONNEMENT

- **Mode Headless** (pour background server / serveurs distants) :
  ```powershell
  .\tools\launch_desktop.ps1 -Headless
  ```
- **Port Personnalisé** :
  ```powershell
  .\tools\launch_desktop.ps1 -Port 8080
  ```

---

## 3. FONCTIONNALITÉS CLÉS DESKTOP

- **Raccourcis Clavier** :
  - `Escape` : Ferme instantanément l'inspecteur d'agent ou la modale d'arbitrage HITL.
  - `s` : Déclenche une synchronisation immédiate de l'état sans attendre le polling.
- **Mode Observer** : Permet de laisser la vue suivre automatiquement les agents en cours de travail.
- **Mode Commander** : Permet d'interagir directement avec n'importe quel collaborateur.
