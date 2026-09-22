# E-ZZIO V9.1 — PROCÉDURE DE RESTAURATION DE LA GOLDEN RELEASE

Ce document décrit la procédure standard de récupération, d'intégrité et de reconstruction pour réinstancier l'environnement **E-ZZIO V9.1 Golden Release** sans ambiguïté.

---

## 1. Localisation des Fichiers de la Baseline

La Golden Release est scellée dans les artefacts suivants :

| Fichier | Rôle | Emplacement |
| :--- | :--- | :--- |
| **Archive Source Complète** | Snapshot immuable de l'ensemble des sources, tests, assets et scripts | [`dist/releases/E-ZzIO-V9.1-GOLDEN-SOURCE.zip`](file:///G:/AI/E-zzio/dist/releases/E-ZzIO-V9.1-GOLDEN-SOURCE.zip) |
| **Manifeste Golden** | Empreintes SHA-256 de contrôle et métadonnées de release | [`dist/releases/E-ZzIO-V9.1-GOLDEN-MANIFEST.json`](file:///G:/AI/E-zzio/dist/releases/E-ZzIO-V9.1-GOLDEN-MANIFEST.json) |
| **Dossier Audit Golden** | Enregistrements forensiques (toolchain, dépendances, tests, runtime) | [`state/audit/golden/v9.1/`](file:///G:/AI/E-zzio/state/audit/golden/v9.1/) |
| **Script de Vérification** | Validateur automatique d'intégrité de la Golden Release | [`tools/verify_golden_release.ps1`](file:///G:/AI/E-zzio/tools/verify_golden_release.ps1) |

---

## 2. Vérification Préalable des Empreintes

Avant toute restauration, vérifier que l'archive n'a subi aucune altération :

```powershell
$Expected = "D3351A86D1BF7FAFF5125CE76E54A5106EF788D84259E1BE9B3B4C37EBEE8A7F"
$Actual = (Get-FileHash -Path "dist/releases/E-ZzIO-V9.1-GOLDEN-SOURCE.zip" -Algorithm SHA256).Hash

if ($Actual -eq $Expected) {
    Write-Host "[OK] Archive Golden Release conforme et authentique." -ForegroundColor Green
} else {
    Write-Error "[FATAL] Altération de l'archive détectée ! Expected: $Expected, Actual: $Actual"
}
```

---

## 3. Procédure de Restauration

### A. Extraction vers un Répertoire Cible Propre
```powershell
$TargetDir = "G:\AI\E-zzio-restored"
Expand-Archive -Path "dist/releases/E-ZzIO-V9.1-GOLDEN-SOURCE.zip" -DestinationPath $TargetDir -Force
Set-Location $TargetDir
```

### B. Configuration de l'Environnement Python
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### C. Vérification de l'Intégrité
Exécuter immédiatement le vérificateur :
```powershell
.\tools\verify_golden_release.ps1
```
Le résultat doit afficher : `GOLDEN_RELEASE_VALID`.

---

## 4. Rejeu de la Suite de Certification

Pour reproduire la certification complète (111 tests) :
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_hitl_approval.py tests/test_hermes_mcp_confinement.py tests/test_federation_smokes.py tests/test_ai_office_visual.py tests/test_ai_office.py tests/test_product_certification.py tests/test_product_lifecycle.py tests/test_hitl_api.py tests/test_hitl_cli.py tests/test_hitl_discord.py tests/test_capability_policy.py tests/test_capability_enforcement.py tests/test_android_project.py tests/test_android_artifact.py tests/test_android_runtime_contract.py tests/test_android_device_gate.py -v
```
Tous les 111 tests doivent être au statut `PASSED`.

---

## 5. Reconstruction des Livrables

### Reconstruction de l'APK Release Android
```powershell
& "tools\build_android_apk.ps1" -Release
```

### Lancement de l'Application Desktop
```powershell
& "tools\launch_desktop.ps1"
```

---

## 6. Création d'une Nouvelle Branche d'Évolution

Pour démarrer un nouveau cycle de développement à partir de cette baseline immuable :
```powershell
git checkout checkpoint/voice-capabilities-hardware-agent-20260816
git switch -c feature/<nom-de-la-fonctionnalite>
```
Ne jamais modifier directement la Golden Release V9.1.
