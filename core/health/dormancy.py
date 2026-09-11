"""Registre des zones dormantes — confinement continu, lecture seule.

Chaque zone : STATUS / OWNER / REASON / RISK / ACTIVATION_PATH /
ACTIVATION_BLOCKED / REVIEW_CONDITION. `verify_containment` prouve par AST
qu'aucun fichier du noyau actif ne les importe (aucune activation silencieuse).
"""
from __future__ import annotations

import ast
import os
from typing import Any, Dict, List

DORMANT_ZONES: List[Dict[str, str]] = [
    {"zone": "src/ezzio", "status": "DORMANT", "owner": "personne (orphelin)",
     "reason": "stack autoporteuse non montée", "risk": "faible",
     "activation_path": "aucun (0 importateur)", "activation_blocked": "oui — non référencé",
     "review": "quarantaine documentée avant toute réactivation"},
    {"zone": "app.py:8000", "status": "DORMANT", "owner": "personne",
     "reason": "stack HTTP non montée (8001 canonique)", "risk": "faible",
     "activation_path": "lancement manuel uniquement", "activation_blocked": "oui — non déployé",
     "review": "déprécier ou documenter desktop-UI"},
    {"zone": "runtime/external/ezzio_app.py", "status": "DORMANT", "owner": "personne",
     "reason": "bridge isolé, 0 accès kernel", "risk": "faible",
     "activation_path": "aucun", "activation_blocked": "oui",
     "review": "archiver si toujours inerte"},
    {"zone": "runtime/core/events.py", "status": "DORMANT", "owner": "personne",
     "reason": "3e bus sans consommateur", "risk": "faible",
     "activation_path": "aucun", "activation_blocked": "oui",
     "review": "archive candidate"},
    {"zone": "runtime/model_router/providers/*", "status": "DORMANT partiellement neutralisé",
     "owner": "registry (donnée)", "reason": "0 consommateur direct ; gemini neutralisé fail-closed",
     "risk": "moyen si réactivé sans vault", "activation_path": "scripts legacy dormants",
     "activation_blocked": "partiel — migrer vers vault avant usage",
     "review": "neutralisation complète ou suppression"},
    {"zone": "providers/ (racine)", "status": "DORMANT-VIVANT", "owner": "registry (donnée)",
     "reason": "chaîne convergence expérimentale", "risk": "moyen",
     "activation_path": "scripts legacy dormants", "activation_blocked": "non — sous surveillance",
     "review": "ne pas réactiver sans audit credential"},
    {"zone": "runtime/memory/WorkingMemory", "status": "LEGACY", "owner": "runtime/kernel_legacy_v2",
     "reason": "supplanté par gateway", "risk": "moyen si réactivé (divergence)",
     "activation_path": "kernel_legacy_v2 uniquement", "activation_blocked": "non — contrat à écrire",
     "review": "quarantaine + contrat de lecture seule"},
    {"zone": "core/evidence (ancien module)", "status": "SUPPRIMÉ",
     "owner": "gateway via core/evidence_store", "reason": "doublon prouvé, test migré",
     "risk": "nul", "activation_path": "aucun", "activation_blocked": "oui — fichier absent",
     "review": "clos"},
    {"zone": "core/capabilities/factory+discovery (CapabilityStatus)",
     "status": "DORMANT-CONTAINED", "owner": "registry canonique",
     "reason": "cycle de vie expressif (11 statuts) cantonné au lab ; "
               "pont unique factory.py:89 convertit vers QualificationStatus "
               "au seul point d'enregistrement ; 0 import noyau",
     "risk": "moyen si câblé au noyau sans revue (double vérité)",
     "activation_path": "runtime/lab/test_v94_autonomous.py uniquement",
     "activation_blocked": "oui — imports noyau interdits (voir BANNED)",
     "review": "ne jamais écrire ACTIVE/RETIRED/DISABLED dans le registre canonique"},
    {"zone": "core/cognitive_router.ModelRouter.complete + core/orchestrator",
     "status": "DORMANT-CONTAINED", "owner": "federation (chemin canonique)",
     "reason": "second chemin d'exécution direct httpx (contourne "
               "federation/registry) ; 0 appelant prod de complete() ; "
               "orchestrateur câblé uniquement via app.py:8000 (dormant) ; "
               "endpoint health routers/master.py n'utilise que get_providers_health",
     "risk": "élevé si câblé au noyau (bypass + clé env directe, modèles périmés)",
     "activation_path": "aucun (app.py non déployé)",
     "activation_blocked": "oui — non référencé par le chemin canonique",
     "review": "supprimer ou réécrire via federation avant toute réactivation ; "
               "ne pas réactiver avec clé env directe"},
    {"zone": "runtime/kernel/boot.py.bak/", "status": "HISTORICAL",
     "owner": "personne", "reason": "sauvegarde pré-nettoyage (v4259, 10 août) ; "
               "référencée par manifests GOLDEN V9.3/V9.4 (historique, ne pas éditer)",
     "risk": "nul (chemin .bak non importable)",
     "activation_path": "aucun", "activation_blocked": "oui — extension non importable",
     "review": "conserver tant que les manifests la référencent"},
    {"zone": "core/cache/response_cache + state/cache/response_cache.db",
     "status": "DORMANT", "owner": "personne",
     "reason": "cache LLM TTL 1h + détection secrets, 0 consommateur prod, "
               "0 test, DB 82Ko stable depuis le 2 sept. (aucune croissance)",
     "risk": "faible (inerte ; réactivation = revue cache-aside + invalidation)",
     "activation_path": "aucun", "activation_blocked": "oui — non référencé",
     "review": "câbler via le chemin canonique ou supprimer si toujours inerte"},
    {"zone": "core/authority/* (policy, evolution_ledger, promotion)",
     "status": "DORMANT-CONTAINED", "owner": "gouvernance canonique (policy fédération)",
     "reason": "sous-système gouvernance V7.32 : 0 import noyau/routers/web ; "
               "EvolutionLedger distinct de l'AuditLedger mais inactif ; "
               "seul consommateur : runtime/tests/authority",
     "risk": "moyen si câblé (double ledger/gouvernance)",
     "activation_path": "aucun", "activation_blocked": "oui — non référencé",
     "review": "fusionner vers AuditLedger+policy avant toute réactivation"},
    {"zone": "core/providers/gemini_pro_provider + schedulers non démarrés",
     "status": "DORMANT", "owner": "personne",
     "reason": "0 importateur ; refresh_service.startup() jamais appelé en prod ; "
               "chaînes Perplexity = docstring, pas de code",
     "risk": "faible",
     "activation_path": "aucun", "activation_blocked": "oui",
     "review": "supprimer après vérification manifests"},
    {"zone": "ResearchRouter.search() historique (first-win séquentiel)",
     "status": "DORMANT-CONTAINED", "owner": "chaîne live (search_all/run_live_research)",
     "reason": "0 appelant prod pour search() ; search_all() + run_live_research() + "
               "run_adaptive_research() actifs (master sur adaptatif) ; "
               "search() conservé intact pour rollback ; Gemini-as-source "
               "désormais exclu du fan-out (Tavily+DDG seuls)",
     "risk": "faible (réactivation = régression multi-source)",
     "activation_path": "aucun", "activation_blocked": "oui — non référencé",
     "review": "supprimer si search_all stable après usage"},
]

# Préfixes dont l'import par le noyau actif est interdit (confinement).
BANNED_KERNEL_IMPORTS = [
    "src.ezzio",
    "runtime.core.events",
    "runtime.model_router.providers",
    "runtime.external.ezzio_app",
    "core.capabilities.factory",
    "core.capabilities.discovery",
]

# Fichiers constituant le noyau actif scanné (pas tout le dépôt : ciblé et rapide).
KERNEL_SCAN_ROOTS = ["core/ezzio_master.py", "core/agent/coder_federation.py",
                     "core/routing/model_registry.py", "web_server.py", "routers"]


def verify_containment(repo_root: str) -> List[Dict[str, Any]]:
    """Retourne les violations (vide = confinement intact)."""
    violations: List[Dict[str, Any]] = []
    targets: List[str] = []
    for root in KERNEL_SCAN_ROOTS:
        p = os.path.join(repo_root, root)
        if os.path.isdir(p):
            for dp, dn, fn in os.walk(p):
                dn[:] = [d for d in dn if d != "__pycache__"]
                targets.extend(os.path.join(dp, f) for f in fn if f.endswith(".py"))
        elif os.path.exists(p):
            targets.append(p)
    for path in targets:
        try:
            tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
        except Exception:
            continue
        for node in ast.walk(tree):
            mods: List[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                mods = [node.module]
            elif isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            for m in mods:
                for banned in BANNED_KERNEL_IMPORTS:
                    if m == banned or m.startswith(banned + "."):
                        violations.append({"file": os.path.relpath(path, repo_root),
                                           "banned_import": m})
    return violations
