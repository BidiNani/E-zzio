# E-ZZIO V10.0 — UNIVERSAL INGESTION CONTRACT & PIPELINE

**Date d'Entrée en Vigueur** : 29 août 2026

---

## 1. LE CONTRAT UNIFIÉ `UniversalIngestionResult`
Tout fichier ou flux réseau ingéré par E-ZzIO retourne une structure de données normalisée, immunisée contre les injections de prompt :

```json
{
  "ok": true,
  "source": "chemin/vers/fichier.csv",
  "filename": "fichier.csv",
  "mime_type": "text/csv",
  "type": "csv",
  "size_bytes": 1024,
  "encoding": "utf-8",
  "content_hash": "a1b2c3d4...",
  "security_flags": [],
  "headers": ["Indicateur", "Valeur"],
  "tables": [{"headers": ["Indicateur", "Valeur"], "rows": [["Latence", "26ms"]]}],
  "content": "Indicateur,Valeur\nLatence,26ms",
  "provenance": "[DONNÉE PASSIVE NON FIABLE]"
}
```

---

## 2. MATRICE COMPLÈTE DES FORMATS SUPPORTÉS

| Famille | Formats Reconnus | Extraction Réalisée | Niveau de Sécurité |
| :--- | :--- | :--- | :---: |
| **Texte Structuré** | `TXT`, `MD`, `PY`, `JSON`, `JSONL`, `YAML`, `TOML`, `LOG`, `SQL`, `INI` | Texte brut, hiérarchie JSON/YAML | **SAFE** |
| **Tabulaire** | `CSV`, `TSV`, `XLSX` | En-têtes, lignes, matrice de données | **SAFE** |
| **Documents Web/Bureautique** | `PDF`, `DOCX`, `PPTX`, `HTML`, `XML`, `RSS`, `ATOM` | Texte intégral, diapositives, tableaux | **SAFE** |
| **Binaire Legacy** | `DOC`, `XLS`, `PPT` (OLE Compound) | Extraction de chaînes résiliente | **SAFE** |
| **Sous-titres & Timings** | `SRT`, `VTT` | Texte consolidé sans métadonnées superflues | **SAFE** |
| **Archives** | `ZIP`, `TAR.GZ` | Manifeste de fichiers (Anti-Zip-Slip & Bomb) | **SAFE** |
| **Images & Visuels** | `PNG`, `JPEG`, `WEBP`, `GIF`, `BMP`, `TIFF`, `SVG` | Dimensions, QR Code direct, routage Vision OCR | **SAFE** |
| **Audio & Vidéo** | `WAV`, `MP3`, `M4A`, `FLAC`, `OGG`, `MP4`, `WEBM`, `MKV`, `AVI` | Routage automatique Faster-Whisper / yt-dlp | **SAFE** |
