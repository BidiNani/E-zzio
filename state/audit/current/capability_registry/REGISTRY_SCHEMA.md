# E-ZZIO CAPABILITY REGISTRY SCHEMA

Le registre canonique `capabilities_registry.json` respecte l'ordre contractuel suivant :

1. `metadata` : Version, timestamp, hash, état général.
2. `providers` : Liste des providers avec statut, type, code_reachable, runtime_reachable, production_active.
3. `credentials` : Noms de variables uniquement (aucun secret exposé).
4. `models` : Modèles physiques, configurés, cloud gouvernés et stale references.
5. `tools` : Capacités de manipulation de fichiers, système, code.
6. `web` : Recherche web, lecteurs, connecteurs de données.
7. `vision` : Moteurs de vision et OCR.
8. `voice` : Synthèse vocale (TTS) et reconnaissance vocale (STT).
9. `documents` : Formats de fichiers pris en charge par le lecteur universel.
10. `interfaces` : Points d'entrée (Discord, Web HUD, CLI, REST API, SDK).
11. `profiles` : Profils de routage (fast, general, coding, deep_reasoning, local_fallback).
12. `rotation` : Spécification des pools de clés et de la rotation multi-projets.
13. `verification` : Synthèse des preuves et niveaux de confiance.
14. `forgotten` : Capacités documentées mais non implémentées ou réfutées.
15. `stale_references` : Références orphelines dans les routeurs ou benchmarks.
