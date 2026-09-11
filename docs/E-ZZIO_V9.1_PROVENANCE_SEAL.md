# E-ZZIO V9.1 — PROVENANCE SEAL & IMMUTABLE GIT BASELINE

**Product**: `E-ZzIO`  
**Version**: `9.0.1` (versionCode `901`)  
**Release**: `V9.1`  
**Git Tag**: `ezzio-v9.1-golden` (Annotated Tag)  
**Golden Commit**: `e12fe3e24ceafe7192a00fd4f26ae144fa6d96d0`  
**Golden Tree**: `672d8ac0c27d42b88159a7f21ee7c9a2edd33fb8`  
**Functional Baseline Commit**: `dde4d186ce8cee1bdcfa42f6850763adb08b25f8`  
**Branch**: `checkpoint/voice-capabilities-hardware-agent-20260816`  
**Status**: `SEALED_IMMUTABLE_BASELINE`  

---

## 1. Identifiants Cryptographiques & Matériels

### A. Empreintes Git Invariables
- **Tag**: `ezzio-v9.1-golden`
- **Commit**: `e12fe3e24ceafe7192a00fd4f26ae144fa6d96d0`
- **Tree**: `672d8ac0c27d42b88159a7f21ee7c9a2edd33fb8`
- **Annotated Tag**: `YES`
- **Cryptographic Git GPG Signature**: `NO (Local Sovereign Keystore, zero public key drift)`

### B. Livrables Binaires & Archives Scellées
- **APK Release**: [`dist/android/E-ZzIO-v9.1-release.apk`](file:///G:/AI/E-zzio/dist/android/E-ZzIO-v9.1-release.apk)  
  `0F62B1A355063BD3436D1513E587E43EB42E77F11A82B260B73CA55595921CDB`  
  *Package*: `ai.ezzio.office` (Production release, non-debuggable)  
  *Signature*: APK Signature Scheme v2 = VERIFIED
- **Archive Source Scellée**: [`dist/releases/E-ZzIO-V9.1-GOLDEN-SOURCE.zip`](file:///G:/AI/E-zzio/dist/releases/E-ZzIO-V9.1-GOLDEN-SOURCE.zip)  
  `D3351A86D1BF7FAFF5125CE76E54A5106EF788D84259E1BE9B3B4C37EBEE8A7F` (301,298,046 octets)
- **Manifeste Golden**: [`dist/releases/E-ZzIO-V9.1-GOLDEN-MANIFEST.json`](file:///G:/AI/E-zzio/dist/releases/E-ZzIO-V9.1-GOLDEN-MANIFEST.json)

### C. Frozen Core Pillars (3/3)
- `core/capabilities/capability_policy.py`: `89A770354EBFE4233697F944F0963C3873B811AF1C7DF73E6DACC7AABB389AE2`
- `core/capabilities/registry.py`: `3EE057B327354FAA95CF72A0A920A5EED4FA5DF77AE87298615ED3860FFB0F68`
- `core/security/audit_ledger.py`: `B26E0D106F0E76121B15B6278F057DEA3ABC1395AA425D86D383E695DFC21C17`

---

## 2. Commandes Officielles de Contrôle

### Commande de Vérification Automatisée de la Golden Release :
```powershell
& pwsh -ExecutionPolicy Bypass -File "tools\verify_golden_release.ps1"
```
Sortie attendue : `GOLDEN_RELEASE_VALID`

### Commande de Restauration :
```powershell
Expand-Archive -Path "dist/releases/E-ZzIO-V9.1-GOLDEN-SOURCE.zip" -DestinationPath "G:\AI\E-zzio-restored" -Force
```

---

## 3. Règle de Développement Futur

Pour toute évolution ultérieure :
```powershell
git switch -c feature/<nom> ezzio-v9.1-golden
```
La Golden Release `ezzio-v9.1-golden` est en lecture seule définitive.
