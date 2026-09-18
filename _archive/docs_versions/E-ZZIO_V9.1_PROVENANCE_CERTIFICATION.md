# E-ZZIO V9.1 — PROVENANCE CERTIFICATION & RELEASE SEAL REPORT

## 1. Golden Release Identity
- **Product**: `E-ZzIO`
- **Version**: `9.0.1` (versionCode `901`)
- **Release**: `V9.1`
- **Status**: `IMMUTABLE_BASELINE (SEALED)`
- **Certification Authority**: Google DeepMind / Sovereign E-ZzIO Pair Programming Agent

## 2. Original Functional Baseline
- **Functional Commit**: `dde4d186ce8cee1bdcfa42f6850763adb08b25f8` (`dde4d18`)
- **Functional Tree**: `dd025aa6d5c3a783f906be1238f7dd98cba0a6b6`
- **Subject**: `fix(registry): rétrocompatibilité schéma 6.1 (routing -> selected) pour EzzioSDK`

## 3. Golden Release Commit
- **Commit ID**: `e12fe3e24ceafe7192a00fd4f26ae144fa6d96d0` (`e12fe3e`)
- **Message**: `release: seal E-ZzIO V9.1 golden baseline`
- **Date**: `2026-09-04T20:44:39+02:00`

## 4. Git Tree
- **Tree Hash**: `672d8ac0c27d42b88159a7f21ee7c9a2edd33fb8`

## 5. Git Tag
- **Tag**: `ezzio-v9.1-golden`
- **Type**: `Annotated Tag`
- **Target**: `e12fe3e24ceafe7192a00fd4f26ae144fa6d96d0`
- **GPG Signing**: `NO (Local sovereign verification, zero remote dependency)`

## 6. Frozen Core
- `core/capabilities/capability_policy.py`: `89A770354EBFE4233697F944F0963C3873B811AF1C7DF73E6DACC7AABB389AE2` (PASS)
- `core/capabilities/registry.py`: `3EE057B327354FAA95CF72A0A920A5EED4FA5DF77AE87298615ED3860FFB0F68` (PASS)
- `core/security/audit_ledger.py`: `B26E0D106F0E76121B15B6278F057DEA3ABC1395AA425D86D383E695DFC21C17` (PASS)

## 7. Test Baseline
- **Regression Suite**: `111/111 PASS` (0 failed, 0 skipped)
- **Gate Test**: `tests/test_android_device_gate.py` (PASS on live hardware/AVD)

## 8. APK
- **Artifact**: `dist/android/E-ZzIO-v9.1-release.apk`
- **Size**: `4,404,215 octets`
- **SHA-256**: `0F62B1A355063BD3436D1513E587E43EB42E77F11A82B260B73CA55595921CDB`
- **Package**: `ai.ezzio.office` (Non-debuggable)
- **Signature**: APK Signature Scheme v2 = `true`

## 9. Golden Archive
- **Archive**: `dist/releases/E-ZzIO-V9.1-GOLDEN-SOURCE.zip`
- **Size**: `301,298,046 octets`
- **SHA-256**: `D3351A86D1BF7FAFF5125CE76E54A5106EF788D84259E1BE9B3B4C37EBEE8A7F`
- **Manifest**: `dist/releases/E-ZzIO-V9.1-GOLDEN-MANIFEST.json`

## 10. Manifest
- **Manifest Path**: `docs/RELEASE_MANIFEST.json`
- **Integrity**: `VERIFIED`

## 11. Security
- **Static Secret Audit**: `PASS (0 secrets detected)`
- **Keystore Isolation**: `release.keystore` excluded and ignored via `.gitignore`

## 12. Tamper Detection
- **Test Script**: `tools/test_tamper_detection.py`
- **Status**: `PASS (Tampering immediately rejected by verifier; restored on clean state)`

## 13. Recovery
- **Test Script**: `tools/test_recovery_archive.py`
- **Status**: `PASS (All essential components and documentation present in archive)`

## 14. Verification Command
```powershell
& pwsh -ExecutionPolicy Bypass -File "tools\verify_golden_release.ps1"
```

## 15. Git State
- **Branch**: `checkpoint/voice-capabilities-hardware-agent-20260816`
- **Tag**: `ezzio-v9.1-golden` pointing directly at HEAD commit `e12fe3e24ceafe7192a00fd4f26ae144fa6d96d0`
- **Tree**: `672d8ac0c27d42b88159a7f21ee7c9a2edd33fb8`

## 16. Future Release Policy
- **Policy**: Read-only baseline.
- **Workflow**: `git switch -c feature/<name> ezzio-v9.1-golden`
- **Upgrades**: Any future changes require a new release (`V9.1.1` / `V9.2` / `V10`).
