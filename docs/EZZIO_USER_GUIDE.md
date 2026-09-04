# 🏛️ GUIDE UTILISATEUR OFFICIEL — E-ZZIO v2.6

Bienvenue dans la documentation officielle d'utilisation d'**E-ZZIO**, le système cognitif souverain autonome.

---

## ⏱️ 5 MINUTES POUR DÉMARRER

### 1. Lancement du Serveur E-ZzIO
Dans un terminal PowerShell sous Windows :
```powershell
python G:\AI\E-zzio\web_server.py
```
Le serveur s'initialise sur `http://127.0.0.1:8001` avec les PRAGMAs NVMe haute performance, le pool de workers et le routeur cognitif Cloud-First.

### 2. Accès à l'Interface Web (HUD)
Ouvrez votre navigateur web à l'adresse :
👉 **`http://127.0.0.1:8001`**

Vous accédez immédiatement au tableau de bord opérationnel temps réel et au chat interactif.

### 3. Poser votre première question
Tapez simplement votre message dans la zone de texte (ex. : *"Bonjour, résume-moi l'architecture d'E-ZzIO"*) ou cliquez sur l'un des boutons d'amorce rapide.

---

## 🖥️ LES 4 INTERFACES UTILISATEUR

E-ZzIO est accessible de manière transparente à travers 4 points d'entrée :

### 1. Web HUD (`http://127.0.0.1:8001`)
- **Chat interactif :** Échange fluide avec sélection du profil cognitif (`Fast`, `General`, `Coding`, `Deep`).
- **Ingestion documentaire par Glisser-Déposer (Drag & Drop) :** Déposez un fichier directement dans la fenêtre ou cliquez sur le bouton trombone (`📎`).
- **Observabilité continue (Lecture seule) :** Visualisation en direct de l'état du Gemini Pool, de Groq, du taux de hit du cache technique et de l'état d'Ollama.

### 2. Bot Discord
Interagissez directement depuis vos salons Discord autorisés (protégés par le `Guardian`) :
- **Conversation générale :** Tapez simplement `!bidi <votre message>`
- **Rappel mémoire :** Tapez `!bidi recall <sujet>` pour retrouver les échanges passés.
- **Vérification d'état :** Tapez `!bidi status` pour afficher l'état de santé du bot.
- **Documents & Images :** Joignez directement un fichier (PDF, image, audio) à votre message `!bidi`.

### 3. Ligne de commande CLI (`ezzio_cli.py`)
Pour exécuter des tâches agentiques ou scripter des actions :
```powershell
# Mode interactif
python G:\AI\E-zzio\ezzio_cli.py

# Exécution d'une tâche ponctuelle
python G:\AI\E-zzio\ezzio_cli.py --task "Analyser le fichier README.md"
```

### 4. API HTTP REST (FastAPI)
Intégrez E-ZzIO dans vos propres scripts et applications :
- `POST /master/chat` : Point d'entrée de chat unifié (`{"text": "votre question", "speed": "fast"}`).
- `POST /perception/upload` : Téléversement et extraction de documents (Multipart Form).
- `POST /perception/perceive` : Analyse d'URLs, flux RSS ou vidéos.
- `GET /metrics` : Télémétrie complète et indicateurs de performance.

---

## 📂 GESTION DES DOCUMENTS & FICHIERS

E-ZzIO intègre un moteur universel de perception documentaire (`UniversalFileReader`) immunisé contre les fausses extensions et les risques de sécurité.

### Formats supportés
- **Documents bureautiques :** `PDF` (PyMuPDF), `DOCX` (Word), `XLSX` (Excel), `PPTX` (PowerPoint).
- **Données tabulaires & Texte :** `CSV`, `TSV`, `HTML`, `TXT`, `MD`, `JSON`.
- **Archives :** `ZIP` (avec protection stricte Anti-Zip-Slip et Anti-Zip-Bomb).
- **Multimédia :** Images (`PNG`, `JPG`, `WEBP`), Audio (`WAV`, `MP3`).

### Comment envoyer un document ?
1. **Via le Web HUD :** Glissez-déposez le fichier dans la fenêtre de chat ou cliquez sur l'icône trombone `📎`.
2. **Attendez le badge de confirmation :** Le HUD affiche un badge `📄 [Nom du fichier] (INGÉRÉ • 12ms)`.
3. **Interrogez E-ZzIO :** Posez votre question (ex. : *"Fais-moi un résumé des points clés du contrat"*).

> **Taille maximale :** 50 Mo par fichier. Les fichiers exécutables déguisés (`.exe`, `.dll`, format PE) sont automatiquement rejetés par sécurité.

---

## 🧠 ROUTAGE COGNITIF & POLITIQUE CLOUD-FIRST

Vous n'avez pas besoin de choisir manuellement vos modèles ou vos clés API. E-ZzIO gère automatiquement le routage cognitif le plus performant et le plus économique via son **ModelRouter souverain**.

### 1. Hiérarchie souveraine
```
Demande Utilisateur
        │
        ▼
[ Cache Technique ] ──(Hit en 0.7ms, 0 Quota)──➔ Réponse Immédiate
        │ (Miss)
        ▼
[ Gemini Pool ] ──────(Primaire Cloud SOTA)─────➔ Réponse Gemini
        │ (Indisponibilité / 429)
        ▼
[ Groq Cloud ] ───────(Amortisseur Same-Role)───➔ Réponse Groq
        │ (Coupure Cloud Totale)
        ▼
[ Ollama Local ] ─────(Dernier Recours CPU)─────➔ Réponse Locale
```

### 2. Niveaux de profils cognitifs
- **`FAST` (Par défaut) :** Réponses instantanées, extractions, factualité (`gemini-3.1-flash-lite`, ~600ms).
- **`GENERAL` :** Synthèse, analyse générale, explications (`gemini-3.6-flash`).
- **`CODING` :** Développement logiciel, refactoring, agentique (`gemini-3.7-flash`).
- **`DEEP` :** Raisonnement complexe, architecture, vérification formelle (`gemini-3.1-pro-preview`).

### 3. Rôle d'Ollama Local
Ollama (`phi4-mini`, `hermes3`, `qwen3.5`) est configuré comme **rideau de dernier recours souverain**. En fonctionnement nominal avec une connexion Internet, le nombre d'appels vers Ollama est strictement égal à **0**, préservant ainsi l'intégralité des ressources CPU/RAM de votre machine.

---

## 🔍 RECHERCHE WEB & LECTURE D'URLS

E-ZzIO peut explorer le web de manière sécurisée et autonome :
- **Recherche Web automatique :** Lorsque votre question nécessite des informations récentes, E-ZzIO interroge les moteurs web (`Tavily` en primaire, repli automatique sur `DuckDuckGo`).
- **Lecture d'URL (Web Crawl) :** Donnez une URL dans votre message ; E-ZzIO extrait le contenu épuré en Markdown.
- **Protection Anti-SSRF :** Tout accès vers des adresses IP locales (`127.0.0.1`, `192.168.x.x`) ou des métadonnées cloud privées (`169.254.169.254`) est physiquement bloqué.

---

## 💾 MÉMOIRE & RAPPEL DE CONTEXTE

E-ZzIO utilise une mémoire unifiée SQLite en mode WAL (`UnifiedMemoryGateway`) :
- **Indexation Full-Text (FTS5 BM25) :** Vos échanges et documents sont indexés en temps réel pour un rappel ultra-rapide (< 10ms).
- **Recherche par mot-clé :** Utilisez `POST /memory/search` ou la commande Discord `!bidi recall <mots-clés>`.

---

## 🎙️ VOIX & PERCEPTION MULTIMODALE

- **Synthèse Vocale (TTS) :** Génération audio haute fidélité via Kokoro-82M ONNX (24 kHz). En cas d'absence des poids neuronaux, le système bascule automatiquement sur un synthétiseur procédural déterministe.
- **Transcription Audio (STT) :** Analyse audio par Faster-Whisper ou streaming temps réel Nemotron ASR.
- **Vision Multimodale :** Posez des questions sur des captures d'écran, schémas ou photographies via `gemini-3.7-flash` ou le moteur local `VisionEngine`.

---

## 🛠️ GUIDE DE DÉPANNAGE & ERREURS FRÉQUENTES

| SYMPTÔME | CAUSE PROBABLE | ACTION UTILISATEUR |
|---|---|---|
| **Erreur "Fichier trop volumineux"** | Fichier > 50 Mo | Réduire la taille du document ou le découper. |
| **Erreur "Format non supporté"** | Extension inconnue ou binaire suspect | Utiliser un format standard (PDF, DOCX, XLSX, TXT, ZIP). |
| **Bascule visible sur Groq dans le HUD** | Gemini a rencontré un 429 ou 503 temporaire | Aucune action requise. Groq absorbe la charge de façon transparente. |
| **Discord : "Accès refusé par le Guardian"** | Nom d'utilisateur non whitelisté | Ajouter l'ID Discord dans `core/integrations/discord/permission_guard.py`. |
| **Erreur de connexion HTTP 8001** | Serveur `web_server.py` arrêté | Relancer `python G:\AI\E-zzio\web_server.py` dans un terminal. |

---

## ❓ FOIRE AUX QUESTIONS (FAQ)

#### Q1 : Quel modèle utilise E-ZzIO ?
> E-ZzIO choisit automatiquement le modèle le plus adapté à votre profil de tâche : `gemini-3.1-flash-lite` pour la rapidité, `gemini-3.6-flash` pour le général, et `gemini-3.7-flash` pour le code.

#### Q2 : Que se passe-t-il si les serveurs Google (Gemini) sont saturés ?
> Le Circuit Breaker d'E-ZzIO bascule instantanément sur Groq Cloud (modèles équivalents `compound` et `qwen`) en moins de 10ms, sans aucune coupure de service.

#### Q3 : Comment puis-je analyser un tableur Excel (.xlsx) ?
> Glissez-déposez simplement le fichier `.xlsx` dans la fenêtre du Web HUD ou joignez-le sur Discord, puis demandez à E-ZzIO d'analyser les colonnes ou de calculer des totaux.

#### Q4 : Mes documents ou clés d'API sont-ils envoyés à des tiers non maîtrisés ?
> Non. Les clés d'API sont encapsulées dans le `SecretsVault` local. Les documents sont analysés localement par le `UniversalFileReader` avant d'être transmis de manière chiffrée uniquement au modèle cognitif sélectionné.

#### Q5 : Comment vérifier que mon cache fonctionne ?
> Observez la carte "Cache Technique" sur le Web HUD : chaque question identique réutilisée voit son temps de réponse chuter à moins de 1 milliseconde avec un compteur de requêtes évitées.