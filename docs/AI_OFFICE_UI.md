# E-ZZIO V9.0 — AI OFFICE UI & LIVING INTERACTION SPECIFICATIONS

## 1. COMPOSANTS DE L'INTERFACE UTILISATEUR

L'interface de **E-ZZIO AI Office** est accessible directement à la racine du serveur web souverain : `http://127.0.0.1:8001/`.

### 1.1 Command Center HUD (Header Supérieur)
- **Indicateur de Souveraineté** : Badge doré `👑 E-ZZIO AGENT HQ V9.0 SOVEREIGN`.
- **Statut Frozen Core** : Badge émeraude pulsant certifiant que les 3 piliers du Frozen Core sont intacts.
- **Compteurs Dynamiques Filtrables** :
  - `TOTAL AGENTS` : 10 agents gouvernés.
  - `WORKING` : Agents actifs en cours d'exécution.
  - `WAITING HITL` : Alertes rouges si une approbation est requise.
  - `DONE` : Tâches achevées avec succès.
- **Synthèse des 4 Fournisseurs Fédérés** :
  - Gemini : 🟢 PASS
  - Groq : 🟢 PASS
  - Ollama : 🟢 PASS
  - Antigravity : 🟠 BLOCKED_BY_EXTERNAL_QUOTA (Fail-safe conforme)
- **Boutons de Contrôle Workspace** :
  - `OBSERVER` : Mode caméra automatique suivant les agents actifs.
  - `COMMANDER` : Mode interactif pour focaliser les agents.
  - `REDUCED MOTION` : Coupure des animations pour accessibilité et économie CPU.
  - `SYNC` : Rafraîchissement forcé.

---

### 1.2 Bannière d'Interception Critique HITL
- Visible uniquement lorsqu'au moins une demande d'approbation est en attente (`ApprovalStatus.PENDING`).
- Fond rouge sombre animé avec effet `glow-red` d'urgence.
- Affiche la capacité interceptée (ex: `drive.write`), l'ID de demande, le résumé sécurisé sans fuite de token, et un compte à rebours en temps réel calculé à partir de la date d'expiration TTL.
- Bouton interactif direct : `[EXAMINER & ARBITRER]` qui ouvre la modale de décision.

---

### 1.3 Canvas Virtuel des 8 Pièces (Grid 2.5D & Avatars Procéduraux)
Chaque zone physique/logique affiche les agents qui lui sont affectés :
1. **Command Center** : Bureau du Gouverneur Suprême E-ZZIO Master.
2. **Dev & Autonomous Lab** : Espace de développement avec Alpha Coder et Hermes Subagent.
3. **Forensics & Research** : Laboratoire d'inspection de Scout Researcher.
4. **Test & Verification Lab** : Station de test continue de Sentinel QA.
5. **Security Vault & Ledger** : Coffre-fort de sécurité gardé par Aegis Guard.
6. **Documentation Chamber** : Atelier de documentation de Chronicle Scribe.
7. **DevOps & MCP Dock** : Quai de dispatch de Nexus DevOps.
8. **Memory & State Core** : Salle des archives SQLite WAL de Mnemosyne Memory.

Chaque carte d'agent affiche :
- Avatar procédural SVG vectoriel léger avec animations CSS (bobbing, typing, anneau de statut).
- Rôle, badge de statut dynamique (`WORKING`, `WAITING_APPROVAL`, `DONE`, `ERROR`, `IDLE`).
- Badge hiérarchique `MASTER` ou `SUB` (indentation visuelle pour les sous-agents).
- Bulle de pensée contextuelle en direct (`bubble`).
- Barre de progression d'exécution réelle.
- Marqueur de liaison de collaboration active (`collaborator_id`).
- Clic interactif ouvrant le tiroir d'inspection détaillée de l'agent.

---

### 1.4 Pipeline de Tâches Vivant (Workflow Trace)
Ligne lumineuse représentant l'avancement gouverné de la tâche active :
```text
PLAN ──► POLICY ──► HITL CHECK ──► RUNNING ──► VERIFY ──► DONE
```
Chaque étape reflète l'état réel du `TaskState` dans `tasks.db`.

---

### 1.5 Inspecteur d'Agent 2.0 (Drawer Latéral)
Permet d'auditer en profondeur un agent sélectionné :
- Identité, rôle exact et parenté.
- Pièce d'affectation et tâche active.
- Bulle de pensée contextuelle.
- Modèle LLM (`gemini-3.7-flash`, `qwen3-coder:30b`, etc.) et fournisseur.
- Outils autorisés sous gouvernance `CapabilityPolicy`.
- Partenaire de collaboration active.
- Logs de terminal réels de l'agent.
- Bouton `Focus Agent` pour centrer la vue.

---

### 1.6 Panneau Live Code & Feed d'Audit
- **Live Code Feed** : Affiche les commits, branches et fichiers récemment touchés par les agents de dev.
- **Sovereign Event Log** : Affiche les derniers événements audités cryptographiquement dans `audit_ledger.db`.
