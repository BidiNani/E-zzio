# E-ZZIO V9.0 — GRAPHIC ASSETS & VISUAL SYSTEM

## 1. Vision & Identity Principle
- **Strict Original Identity**: E-ZZIO visual elements, avatars, rooms, and badges are strictly original.
- **Prohibited Franchises**: Absolute zero usage or copy of sprites from *The Escapists*, *The Office*, or commercial copyrighted games.
- **Procedural Engine Priority**: Procedural SVG and pure CSS are favored over large static raster packs, providing zero network latency, infinite scalability, and immediate offline availability.

---

## 2. Asset Manifest (`assets/ASSET_LICENSES.json`)
All graphic components and typography are cataloged in [`assets/ASSET_LICENSES.json`](file:///G:/AI/E-zzio/assets/ASSET_LICENSES.json).

### 2.1 Procedural Agent Avatars (`generateAvatarSvg`)
- **Location**: Inlined directly in [`runtime/web/index.html`](file:///G:/AI/E-zzio/runtime/web/index.html).
- **Format**: Dynamic SVG vector markup generated per agent profile.
- **Palette**: Procedural color themes per specialization (Command, Dev, Research, Security, QA, DevOps, Memory, External).
- **Expressions & States**: Real-time rendering of `IDLE`, `WORKING`, `WAITING_APPROVAL`, `ERROR`, `DONE`.

### 2.2 Sovereign Application Icon (`assets/ui/icon.svg`)
- **Dimensions**: 512x512 vector SVG.
- **Design**: Sovereign shield, dark slate background, gold tactical crown, cyan border accents, and verified jewel studs.
- **License**: Apache-2.0 / E-ZZIO Sovereign Open-Source.

### 2.3 Typography
- **UI Font**: `Inter` (SIL Open Font License 1.1) with system-ui fallbacks.
- **Monospace Font**: `Fira Code` (SIL Open Font License 1.1) with ui-monospace and Consolas fallbacks.
