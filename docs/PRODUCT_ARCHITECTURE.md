# E-ZZIO V9.0 — PRODUCT ARCHITECTURE

## 1. VISION DU PRODUIT MULTI-CLIENT

E-ZZIO V9.0 n'est plus une collection de scripts disparates mais un **logiciel complet, souverain et distribuable** capable d'opérer de façon transparente sur **Desktop (Windows)**, **Web (Local & Réseau)** et **Mobile (Android APK)**.

```text
                     👑 E-ZZIO SOVEREIGN CORE
               (CapabilityPolicy · HITL · AuditLedger)
                                │
                     FastAPI REST & WebSocket
                         (Port 8001)
                                │
                Event / State Telemetry Layer
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
   💻 Desktop Client       🌐 Web Browser        📱 Android Client
   (Windows Native PWA    (PWA Standalone +      (Native APK WebView +
    Launcher / WebView2)   Service Worker)        WebSocket Client)
         │                      │                      │
         └──────────────────────┴──────────────────────┘
                                │
                    LIVING AI OFFICE WORKSPACE
                 (8 Rooms · 10 Agents · 2.5D HUD)
```

---

## 2. CLIENTS DISTRIBUÉS & COHÉRENCE MULTI-ÉCRANS

| Client | Plateforme | Rôle UX & Mode de Fonctionnement |
| :--- | :--- | :--- |
| **Desktop Windows** | Windows 10/11 | Application de contrôle plein écran (lanceur `tools/launch_desktop.ps1` via WebView2/PWA standalone). Idéal pour les configurations multi-écrans 1080p/1440p. |
| **Web PWA** | Tout navigateur moderne | Service Worker local (`runtime/web/sw.js`), manifest web (`runtime/web/manifest.json`), tolérance réseau et mise en cache hors-ligne. |
| **Android APK** | Android 8.0+ (SDK 26-34) | Package natif distribuable (`dist/android/E-ZzIO-v9.0.0.apk`), tactile d'abord (barre inférieure sticky, drawer tactile, zoom, alertes vibratoires). |

---

## 3. PRINCIPES DE SÉCURITÉ & NON-EXPOSITION DES SECRETS

1. **Isolation des Clés d'API** : L'APK et le bundle web ne contiennent aucune clé d'API (zéro token Gemini, Groq, Discord ou mot de passe).
2. **Autorité Unique** : Toute action mutatrice (ex: `drive.write`, `github.push`) passe impérativement par `CapabilityPolicy.evaluate_scope(...)` et exige l'approbation humaine `REQUIRE_HUMAN`.
3. **Consistance Multi-Client** : Lorsqu'une demande HITL est générée, elle est immédiatement synchronisée sur Desktop et Android avec le même `approval_id`. L'approbation effectuée depuis l'Android met instantanément à jour le Desktop.
