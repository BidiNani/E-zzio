# E-ZZIO V10.0 — CAPABILITY ACQUISITION POLICY V1

---

## 1. MATRICE DE DÉCISION D'ACQUISITION

| Niveau de Risque | Type de Capacité | Action E-ZzIO | Approbation Humaine |
| :--- | :--- | :--- | :---: |
| **Faible (LOW)** | Outil local read-only, CLI déterministe, parser | Acquisition automatique en Sandbox | NON |
| **Moyen (MEDIUM)** | Moteur multimédia lourd (LTX, LivePortrait, Kokoro) | Installation en Sandbox externe + Tests | NON |
| **Élevé (HIGH)** | Nouveau provider Cloud, accès mutation externe | Pré-qualification + demande explicite | **OUI** (`REQUIRE_HUMAN`) |
| **Critique (CRITICAL)** | Modification d'une autorité du Core V9.0 | Rejet immédiat / Architecture Gate | **OUI** (Gate requise) |
