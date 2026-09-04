# E-ZZIO V9.0 — PERFORMANCE BASELINE

**Date de Mesure** : 29 août 2026  
**Environnement** : AMD Ryzen 9 5900X (12C/24T), 64 Go RAM, NVMe PCIe 4.0, Windows 11 Pro, Python 3.12.10

---

## 1. TABLEAU COMPARATIF DES PERFORMANCES

| Opération / Endpoint | Baseline Historique (v1.0) | Après Assainissement (v3.0) | Gel V9.0 (Freeze Actuel) | Statut & Gain |
| :--- | :---: | :---: | :---: | :--- |
| **Démarrage Uvicorn** | ~2.5s | < 1.2s | **< 1.0s** | Gain net |
| **`GET /health`** | 120 ms | 45 ms | **26.37 ms** | **-78% latence** |
| **`GET /metrics`** | 180 ms | 95 ms | **64.62 ms** | **-64% latence** |
| **`GET /capabilities`** | 85 ms | 12 ms | **1.30 ms** | **-98% latence** |
| **`GET /perception/status`** | 60 ms | 10 ms | **0.98 ms** | **-98% latence** |
| **`POST /master/chat` (Gemini)** | ~2.40s | ~1.40s | **1.24s** | Inférence Cloud fluide |
| **Durée Suite Pytest Complète** | 262.78s | 95.87s | **85.63s (308 tests)** | **-67% temps total** |
