"""
E-ZZIO Core — Codebase Map Reader (Auto-Connaissance Déterministe).
Permet à CognitiveGateway et aux composants du Core d'interroger la cartographie
structurelle et physique du dépôt sans créer de mémoire concurrente.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

class CodebaseMapReader:
    """Lecteur optimisé en lecture seule de la cartographie E-ZZIO."""

    def __init__(self, root_dir: Optional[str] = None):
        if root_dir:
            self.root_dir = Path(root_dir).resolve()
        else:
            self.root_dir = Path(__file__).resolve().parent.parent.parent

        self.mapping_dir = self.root_dir / "state" / "audit" / "current" / "mapping"
        self.docs_map_file = self.root_dir / "docs" / "EZZIO_MAP.md"

        self._dep_graph: Optional[Dict[str, Any]] = None
        self._content_sum: Optional[Dict[str, Any]] = None
        self._entrypoint_chains: Optional[Dict[str, Any]] = None

    def _load_data(self) -> None:
        if self._dep_graph is None:
            dep_file = self.mapping_dir / "dependency_graph.json"
            if dep_file.exists():
                try:
                    self._dep_graph = json.loads(dep_file.read_text(encoding="utf-8"))
                except Exception:
                    self._dep_graph = {}
            else:
                self._dep_graph = {}

        if self._content_sum is None:
            sum_file = self.mapping_dir / "content_summary.json"
            if sum_file.exists():
                try:
                    self._content_sum = json.loads(sum_file.read_text(encoding="utf-8"))
                except Exception:
                    self._content_sum = {}
            else:
                self._content_sum = {}

        if self._entrypoint_chains is None:
            chain_file = self.mapping_dir / "entrypoint_chains.json"
            if chain_file.exists():
                try:
                    self._entrypoint_chains = json.loads(chain_file.read_text(encoding="utf-8"))
                except Exception:
                    self._entrypoint_chains = {}
            else:
                self._entrypoint_chains = {}

    def get_overview(self) -> str:
        """Retourne la synthèse globale de l'architecture (docs/EZZIO_MAP.md)."""
        if self.docs_map_file.exists():
            try:
                return self.docs_map_file.read_text(encoding="utf-8")
            except Exception:
                pass
        return "Cartographie E-ZZIO non disponible."

    def lookup_file(self, rel_path: str) -> Optional[Dict[str, Any]]:
        """Renvoie les informations détaillées d'un fichier spécifique."""
        self._load_data()
        norm_path = rel_path.replace("\\", "/").strip("/")
        
        info = {}
        if self._content_sum and norm_path in self._content_sum:
            info["summary"] = self._content_sum[norm_path]
        if self._dep_graph and norm_path in self._dep_graph:
            info["dependencies"] = self._dep_graph[norm_path]
            
        return info if info else None

    def query_context(self, user_query: str) -> str:
        """Recherche sémantique ciblée dans la cartographie pour enrichir CognitiveGateway."""
        self._load_data()
        query_lower = user_query.lower()

        # Détection de mots-clés spécifiques
        matched_files = []
        
        # 1. Recherche directe par chemin de fichier
        for path, data in (self._content_sum or {}).items():
            path_name = os.path.basename(path).lower()
            if path.lower() in query_lower or (len(path_name) > 4 and path_name in query_lower):
                matched_files.append((path, data, "exact_file_match"))
                
        # 2. Recherche par concept fonctionnel
        keywords_map = {
            "chiffrement": ["core/security/secrets_vault.py", "core/security/audit_ledger.py"],
            "secret": ["core/security/secrets_vault.py"],
            "vault": ["core/security/secrets_vault.py"],
            "memoire": ["core/memory/unified_gateway.py", "core/evidence_store.py"],
            "memory": ["core/memory/unified_gateway.py"],
            "fts5": ["core/memory/unified_gateway.py"],
            "routeur": ["core/cognition/model_router.py"],
            "router": ["core/cognition/model_router.py"],
            "gateway": ["core/cognition/cognitive_gateway.py"],
            "sdk": ["core/sdk.py"],
            "discord": ["core/integrations/discord/discord_client.py"],
            "sheet": ["core/generators/sheet_engine.py"],
            "pdf": ["core/generators/pdf_engine.py"],
            "tts": ["core/capabilities/kokoro_tts_adapter.py"],
            "vision": ["core/providers/nvidia_nim_provider.py"],
            "patch": ["core/agent/patch_engine.py"]
        }

        for kw, paths in keywords_map.items():
            if kw in query_lower:
                for p in paths:
                    if self._content_sum and p in self._content_sum:
                        matched_files.append((p, self._content_sum[p], f"keyword:{kw}"))

        if not matched_files:
            return ""

        # Déduplication
        seen = set()
        unique_matches = []
        for p, data, reason in matched_files:
            if p not in seen:
                seen.add(p)
                unique_matches.append((p, data))

        # Construction de l'extrait contextuel
        lines = ["[AUTO-CONNAISSANCE DE LA CODEBASE — SOURCE: CARTOGRAPHIE FORENSIQUE RÉELLE]"]
        for p, data in unique_matches[:5]:
            dep_info = (self._dep_graph or {}).get(p, {})
            imported_by = dep_info.get("imported_by", [])
            imports = dep_info.get("imports", [])
            lines.append(f"- Fichier: `{p}`")
            lines.append(f"  Rôle: {data.get('role', 'N/A')}")
            lines.append(f"  Classes/Fonctions: {', '.join(data.get('classes', []) + data.get('functions', [])[:4])}")
            lines.append(f"  Dépendants (Importé par {len(imported_by)} fichiers): {', '.join(imported_by[:6])}{'...' if len(imported_by) > 6 else ''}")
            lines.append(f"  Dépendances internes ({len(imports)} fichiers): {', '.join(imports[:6])}{'...' if len(imports) > 6 else ''}")

        return "\n".join(lines)

codebase_map_reader = CodebaseMapReader()
