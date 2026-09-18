import ast
import logging
from pathlib import Path

logger = logging.getLogger("ezzio.scope_resolver")


class DomainScopeResolver:
    """Résout le graphe de dépendances et extrait le scope de fichiers par domaine (V49.2)."""

    DOMAIN_SEEDS: dict[str, list[str]] = {
        "memory": [
            "core/memory/unified_gateway.py",
            "core/memory_core.py",
            "core/evidence_store.py",
        ],
        "router": [
            "core/decision_router.py",
            "core/router/intent_router.py",
            "core/research_router.py",
        ],
        "security": [
            "core/security/guardrail.py",
            "core/security/quota_manager.py",
            "core/security/ledger_engine.py",
        ],
        "discord": [
            "core/integrations/discord/discord_client.py",
        ],
    }

    def __init__(self, root_dir: str | None = None):
        self.root = Path(root_dir).resolve() if root_dir else Path.cwd().resolve()
        self._dep_graph: dict[str, set[str]] = {}
        self._reverse_dep_graph: dict[str, set[str]] = {}
        self._missing_seeds: dict[str, list[str]] = {}
        self._validate_seeds()
        self.build_dependency_graph()

    def _validate_seeds(self):
        for domain, seeds in self.DOMAIN_SEEDS.items():
            missing = [s for s in seeds if not (self.root / s).exists()]
            if missing:
                self._missing_seeds[domain] = missing
                logger.warning(
                    "[SCOPE RESOLVER] Domaine '%s' : %d/%d seed(s) introuvable(s) : %s. Le scope résolu sera incomplet ou vide.",
                    domain,
                    len(missing),
                    len(seeds),
                    missing,
                )

    EXCLUDED_DIRS: set[str] = {
        ".venv",
        ".venv_311_archive",
        ".venv_312",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "quarantine",
        "_archive",
        "_backups_auto",
    }

    def _should_exclude(self, path: Path) -> bool:
        return any(part in self.EXCLUDED_DIRS or part.startswith(".venv") for part in path.parts)

    def _normalize_path(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def build_dependency_graph(self):
        """Indexe les imports statiques entre fichiers propriétaires via l'AST."""
        source_dirs = ["core", "routers", "interfaces", "tools", "tests"]
        py_files = []
        for sdir in source_dirs:
            sp = self.root / sdir
            if sp.exists():
                for py_file in sp.rglob("*.py"):
                    if not self._should_exclude(py_file):
                        py_files.append(py_file)

        for py_file in py_files:

            rel_path = self._normalize_path(py_file)
            self._dep_graph.setdefault(rel_path, set())

            try:
                # FIX VITAL : utf-8-sig gère et supprime automatiquement le BOM (U+FEFF) de Windows
                source = py_file.read_text(encoding="utf-8-sig", errors="ignore")
                tree = ast.parse(source, filename=str(py_file))

                for node in ast.walk(tree):
                    target_module = None
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            target_module = alias.name
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        target_module = node.module

                    if target_module and (
                        target_module.startswith("core") or target_module.startswith("runtime") or target_module.startswith("interfaces")
                    ):
                        candidate = self.root / (target_module.replace(".", "/") + ".py")
                        if candidate.exists():
                            norm_candidate = self._normalize_path(candidate)
                            self._dep_graph[rel_path].add(norm_candidate)
                            self._reverse_dep_graph.setdefault(norm_candidate, set()).add(rel_path)

            except SyntaxError as e:
                logger.error("[SCOPE RESOLVER] SyntaxError réelle dans %s (ligne %s): %s", rel_path, e.lineno, e.msg)
            except Exception as e:
                logger.debug("Parsing AST ignoré pour %s: %s", rel_path, e)

    def resolve_scope(self, domain: str, max_depth: int = 1) -> list[str]:
        if domain not in self.DOMAIN_SEEDS:
            logger.info("[SCOPE RESOLVER] Domaine '%s' non déclaré dans DOMAIN_SEEDS.", domain)
            return []

        seeds = self.DOMAIN_SEEDS[domain]
        existing_seeds = [s for s in seeds if (self.root / s).exists()]

        if not existing_seeds:
            logger.error(
                "[SCOPE RESOLVER] Domaine '%s' déclaré mais AUCUN seed n'existe (%s). Scope vide retourné — erreur de configuration.",
                domain,
                seeds,
            )
            return []

        resolved: set[str] = set()
        queue = [(s, 0) for s in existing_seeds]

        while queue:
            current, depth = queue.pop(0)
            if current in resolved or depth > max_depth:
                continue
            resolved.add(current)

            for dep in self._dep_graph.get(current, []):
                if dep not in resolved:
                    queue.append((dep, depth + 1))

            for rdep in self._reverse_dep_graph.get(current, []):
                if rdep not in resolved:
                    queue.append((rdep, depth + 1))

        scope = sorted(list(resolved))
        logger.info("[SCOPE RESOLVER] Domaine '%s' résolu à %d fichiers.", domain, len(scope))
        return scope
