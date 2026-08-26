from fastapi import APIRouter, HTTPException
from core.schemas import KnowledgeRequest
from core.knowledge_connectors import (
    knowledge_status,
    wikipedia_summary,
    wikipedia_search,
    wikidata_search,
    wikidata_sparql,
    stackexchange_search,
    arxiv_search,
    crossref_search,
    openmeteo_forecast,
    nominatim_search,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/status")
async def status():
    return knowledge_status()


@router.post("/search")
async def search(req: KnowledgeRequest):
    provider = req.provider.lower().strip()

    try:
        if provider in ["wiki", "wikipedia"]:
            mode = req.params.get("mode", "search")
            if mode == "summary":
                return wikipedia_summary(req.query, lang=req.lang, compress=req.compress)
            return wikipedia_search(req.query, lang=req.lang, limit=req.limit, compress=req.compress)

        if provider == "wikidata":
            mode = req.params.get("mode", "search")
            if mode == "sparql":
                return wikidata_sparql(req.query, compress=req.compress)
            return wikidata_search(req.query, lang=req.lang, limit=req.limit, compress=req.compress)

        if provider in ["stackexchange", "stackoverflow"]:
            site = req.params.get("site", "stackoverflow")
            return stackexchange_search(req.query, site=site, limit=req.limit, compress=req.compress)

        if provider == "arxiv":
            return arxiv_search(req.query, limit=req.limit, compress=req.compress)

        if provider == "crossref":
            return crossref_search(req.query, limit=req.limit, compress=req.compress)

        if provider in ["meteo", "weather", "openmeteo"]:
            lat = req.params.get("latitude")
            lon = req.params.get("longitude")
            if lat is None or lon is None:
                raise HTTPException(status_code=400, detail="latitude et longitude requis pour Open-Meteo.")
            return openmeteo_forecast(lat, lon, compress=req.compress)

        if provider in ["osm", "nominatim", "map"]:
            return nominatim_search(req.query, limit=req.limit, compress=req.compress)

        raise HTTPException(status_code=400, detail="Provider refusé.")
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
