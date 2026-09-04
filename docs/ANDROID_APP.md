# E-ZZIO V9.0 — ANDROID APPLICATION & APK GUIDE

## 1. COMPILATION ET PACKAGING DU PACKAGE APK

Pour générer le fichier distribuable `E-ZzIO-v9.0.0.apk` :

```powershell
.\tools\build_android_apk.ps1
```

L'artefact est généré sous :
```text
dist/android/E-ZzIO-v9.0.0.apk
```

### 1.1 Contrôle d'Intégrité et Sécurité
Le script de build effectue un scan statique de sécurité vérifiant qu'aucun token, clé secrète ou mot de passe n'est embarqué dans le code source de l'application mobile.

---

## 2. INSTALLATION SUR SMARTPHONE OU ÉMULATEUR

1. **Autoriser les sources inconnues** sur votre périphérique Android (Paramètres > Sécurité > Installer des applications inconnues).
2. **Transférer l'APK** sur le smartphone via USB, adb ou téléchargement local :
   ```bash
   adb install dist/android/E-ZzIO-v9.0.0.apk
   ```
3. **Connexion Réseau Local (Wi-Fi)** :
   - Assurez-vous que le PC hébergeant E-ZZIO et le smartphone sont connectés sur le même réseau Wi-Fi.
   - Saisissez l'adresse IP locale du PC (ex: `http://192.168.1.50:8001/`).
   - Sous émulateur Android Studio, l'alias canonique est `http://10.0.2.2:8001/`.

---

## 3. EXPÉRIENCE TACTILE ET NOTIFICATIONS HITL

- **Barre Inférieure Mobile** : Accès direct en un clic (`HQ`, `OFFICE`, `TASKS`, `HITL`, `LOGS`).
- **Badge d'Alerte HITL** : Lorsqu'un agent requiert une validation (`REQUIRE_HUMAN`), un badge rouge pulsant apparaît sur l'onglet HITL.
- **Arbitrage Sécurisé** : L'utilisateur consulte le `safe_summary` (exempt de tout secret) et valide ou refuse l'action (`APPROVE` / `REJECT`).
