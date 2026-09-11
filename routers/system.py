import os
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from typing import List, Optional

from core.system_cleanup import SystemCleanupService
from core.dependency_graph_v49 import DependencyGraphV49

logger = logging.getLogger("ezzio.routers.system")

router = APIRouter(prefix="/api/v1/system", tags=["System"])

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
EXPECTED_KEY = os.getenv("EZZIO_API_KEY", "ezzio_secret_key_local_dev")

# ---------------------------------------------------------------------------
# CLEANUP
# ---------------------------------------------------------------------------


class CleanupRequest(BaseModel):
    dry_run: bool = True
    remove_logs: bool = True
    remove_temp: bool = True
    remove_archives: bool = True


class CleanupReport(BaseModel):
    folders_removed: List[str] = []
    folders_skipped: List[str] = []
    files_removed: List[str] = []
    files_skipped: List[str] = []
    space_freed_bytes: int = 0
    error: Optional[str] = None


@router.post("/cleanup", response_model=CleanupReport)
async def system_cleanup(request: CleanupRequest, api_key: str = Depends(api_key_header)):
    if api_key != EXPECTED_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")

    service = SystemCleanupService()
    res = service.run_cleanup(
        dry_run=request.dry_run, remove_logs=request.remove_logs, remove_temp=request.remove_temp, remove_archives=request.remove_archives
    )
    return CleanupReport(**res)


# ---------------------------------------------------------------------------
# DEPENDENCIES (V49)
# ---------------------------------------------------------------------------


class DependencyGraphResponse(BaseModel):
    total_files: int
    total_modules: int
    orphans: List[str]
    circular_dependencies: List[List[str]]
    graph_path: str


class DependencyQueryRequest(BaseModel):
    files: List[str]
    include_transitive: bool = True


class DependencyQueryResponse(BaseModel):
    closure: List[str]
    direct_dependencies: List[str]
    dependents: List[str]


@router.get("/dependencies", response_model=DependencyGraphResponse, tags=["Dependencies"])
async def get_dependency_graph(api_key: str = Depends(api_key_header)):
    """
    Retourne le graphe de dépendances complet (V49).
    """
    if api_key != EXPECTED_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")

    graph = DependencyGraphV49()
    graph.build()

    # Exporter le graphe
    graph_path = graph.export_json()

    return DependencyGraphResponse(
        total_files=len(graph.import_map),
        total_modules=len(graph.reverse_map),
        orphans=graph.find_orphans(),
        circular_dependencies=[list(pair) for pair in graph.find_circular_dependencies()],
        graph_path=graph_path,
    )


@router.post("/dependencies/query", response_model=DependencyQueryResponse, tags=["Dependencies"])
async def query_dependencies(request: DependencyQueryRequest, api_key: str = Depends(api_key_header)):
    """
    Interroge le graphe de dépendances pour un ensemble de fichiers.
    Retourne la fermeture transitive (si include_transitive=True).
    """
    if api_key != EXPECTED_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")

    graph = DependencyGraphV49()
    graph.build()

    if request.include_transitive:
        closure = graph.get_transitive_closure(request.files)
    else:
        closure = set(request.files)

    # Direct dependencies
    direct_deps = set()
    for filepath in request.files:
        direct_deps.update(graph.get_dependencies(filepath))

    # Dependents (fichiers qui importent ces fichiers)
    dependents = set()
    for filepath in request.files:
        module = graph.file_to_module.get(filepath, "")
        if module:
            dependents.update(graph.get_dependents(module))

    return DependencyQueryResponse(closure=sorted(closure), direct_dependencies=sorted(direct_deps), dependents=sorted(dependents))


@router.get("/dependencies/orphans", response_model=List[str], tags=["Dependencies"])
async def get_orphan_files(api_key: str = Depends(api_key_header)):
    """
    Retourne la liste des fichiers orphelins (aucun import, aucun fichier ne les importe).
    """
    if api_key != EXPECTED_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")

    graph = DependencyGraphV49()
    graph.build()

    return graph.find_orphans()


@router.get("/dependencies/circular", response_model=List[List[str]], tags=["Dependencies"])
async def get_circular_dependencies(api_key: str = Depends(api_key_header)):
    """
    Retourne la liste des dépendances circulaires détectées.
    """
    if api_key != EXPECTED_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")

    graph = DependencyGraphV49()
    graph.build()

    return [list(pair) for pair in graph.find_circular_dependencies()]


# ---------------------------------------------------------------------------
# EXPORT GRAPHVIZ / JSON (V49)
# ---------------------------------------------------------------------------


class ExportGraphRequest(BaseModel):
    format: str = "dot"


class ExportGraphResponse(BaseModel):
    file_path: str
    format: str


@router.post("/dependencies/export", response_model=ExportGraphResponse)
async def export_dependency_graph(request: ExportGraphRequest, api_key: str = Depends(api_key_header)):
    if api_key != EXPECTED_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")

    graph = DependencyGraphV49()
    graph.build()

    if request.format == "dot":
        file_path = graph.export_graphviz()
    else:
        file_path = graph.export_json()

    return ExportGraphResponse(file_path=file_path, format=request.format)


# ---------------------------------------------------------------------------
# CLEANUP ORPHANS (V49)
# ---------------------------------------------------------------------------


class OrphanCleanupRequest(BaseModel):
    dry_run: bool = True


class OrphanCleanupReport(BaseModel):
    orphans_found: List[str]
    orphans_removed: List[str]
    space_freed_bytes: int = 0


@router.post("/cleanup/orphans", response_model=OrphanCleanupReport)
async def cleanup_orphans(request: OrphanCleanupRequest, api_key: str = Depends(api_key_header)):
    if api_key != EXPECTED_KEY:
        raise HTTPException(status_code=403, detail="Clé API invalide")

    graph = DependencyGraphV49()
    graph.build()

    orphans = graph.find_orphans()
    removed = []
    space_freed = 0

    if not request.dry_run:
        for orphan in orphans:
            try:
                filepath = graph.project_root / orphan
                size = filepath.stat().st_size
                filepath.unlink()
                removed.append(orphan)
                space_freed += size
            except Exception as e:
                logger.warning("[WARN] Impossible de supprimer %s : %s", orphan, e)

    return OrphanCleanupReport(orphans_found=orphans, orphans_removed=removed, space_freed_bytes=space_freed)
