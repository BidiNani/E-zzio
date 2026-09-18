import os
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

from core.cloud_guard import cloud_status, guarded_request
from core.token_compressor import compact_api_result

PROJECT_ROOT = Path("G:/AI/E-zzio")
SECRETS_PATH = PROJECT_ROOT / "secrets" / ".env"

load_dotenv(SECRETS_PATH)


def user_agent():
    return os.getenv("EZZIO_USER_AGENT", "E-ZZIO-local/1.0 (contact: enrik.pani@gmail.com)").strip()


def headers_json():
    return {
        "User-Agent": user_agent(),
        "Accept": "application/json",
    }


def wikipedia_summary(title, lang="fr", compress=True):
    lang = "en" if lang not in ["fr", "en"] else lang
    safe_title = quote(str(title).replace(" ", "_"))
    result = guarded_request(
        "GET",
        f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{safe_title}",
        headers=headers_json(),
        cache=True,
        cache_ttl=86400,
    )
    return compact_api_result(result, max_chars=4000) if compress else result


def wikipedia_search(query, lang="fr", limit=5, compress=True):
    lang = "en" if lang not in ["fr", "en"] else lang
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "utf8": 1,
        "srlimit": max(1, min(int(limit), 20)),
    }
    result = guarded_request(
        "GET",
        f"https://{lang}.wikipedia.org/w/api.php",
        headers=headers_json(),
        params=params,
        cache=True,
        cache_ttl=3600,
    )
    return compact_api_result(result, max_chars=5000) if compress else result


def wikidata_search(query, lang="fr", limit=5, compress=True):
    params = {
        "action": "wbsearchentities",
        "search": query,
        "language": lang,
        "format": "json",
        "limit": max(1, min(int(limit), 20)),
    }
    result = guarded_request(
        "GET",
        "https://www.wikidata.org/w/api.php",
        headers=headers_json(),
        params=params,
        cache=True,
        cache_ttl=86400,
    )
    return compact_api_result(result, max_chars=5000) if compress else result


def wikidata_sparql(query, compress=True):
    params = {
        "query": query,
        "format": "json",
    }
    result = guarded_request(
        "GET",
        "https://query.wikidata.org/sparql",
        headers=headers_json(),
        params=params,
        cache=True,
        cache_ttl=86400,
        timeout=35,
    )
    return compact_api_result(result, max_chars=7000) if compress else result


def stackexchange_search(query, site="stackoverflow", limit=5, compress=True):
    params = {
        "order": "desc",
        "sort": "relevance",
        "intitle": query,
        "site": site,
        "pagesize": max(1, min(int(limit), 20)),
        "filter": "default",
    }
    key = os.getenv("STACKEXCHANGE_KEY", "").strip()
    if key:
        params["key"] = key

    result = guarded_request(
        "GET",
        "https://api.stackexchange.com/2.3/search",
        headers=headers_json(),
        params=params,
        cache=True,
        cache_ttl=1800,
    )
    return compact_api_result(result, max_chars=6000) if compress else result


def arxiv_search(query, limit=5, compress=True):
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max(1, min(int(limit), 20)),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    result = guarded_request(
        "GET",
        "https://export.arxiv.org/api/query",
        headers={"User-Agent": user_agent(), "Accept": "application/atom+xml"},
        params=params,
        cache=True,
        cache_ttl=7200,
        timeout=35,
    )
    return compact_api_result(result, max_chars=7000) if compress else result


def crossref_search(query, limit=5, compress=True):
    params = {
        "query": query,
        "rows": max(1, min(int(limit), 20)),
    }
    mailto = os.getenv("CROSSREF_MAILTO", "").strip()
    if mailto:
        params["mailto"] = mailto

    result = guarded_request(
        "GET",
        "https://api.crossref.org/works",
        headers=headers_json(),
        params=params,
        cache=True,
        cache_ttl=7200,
    )
    return compact_api_result(result, max_chars=7000) if compress else result


def openmeteo_forecast(latitude, longitude, compress=True):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,precipitation_probability",
        "forecast_days": 2,
        "timezone": "auto",
    }
    result = guarded_request(
        "GET",
        "https://api.open-meteo.com/v1/forecast",
        headers=headers_json(),
        params=params,
        cache=True,
        cache_ttl=900,
    )
    return compact_api_result(result, max_chars=5000) if compress else result


def nominatim_search(query, limit=5, compress=True):
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": max(1, min(int(limit), 10)),
        "addressdetails": 1,
    }
    result = guarded_request(
        "GET",
        "https://nominatim.openstreetmap.org/search",
        headers=headers_json(),
        params=params,
        cache=True,
        cache_ttl=86400,
    )
    return compact_api_result(result, max_chars=5000) if compress else result


def knowledge_status():
    return {
        "cloud_guard": cloud_status(),
        "providers": {
            "wikipedia": {
                "enabled": True,
                "auth": "none",
                "use": "encyclopédie, définitions, contexte général",
            },
            "wikidata": {
                "enabled": True,
                "auth": "none",
                "use": "faits structurés, entités, SPARQL",
            },
            "stackexchange": {
                "enabled": True,
                "auth": "optional key",
                "use": "debug, erreurs, pratiques dev",
            },
            "arxiv": {
                "enabled": True,
                "auth": "none",
                "use": "papiers scientifiques",
            },
            "crossref": {
                "enabled": True,
                "auth": "none, mailto conseillé",
                "use": "métadonnées DOI, recherche académique",
            },
            "openmeteo": {
                "enabled": True,
                "auth": "none",
                "use": "météo gratuite non commerciale",
            },
            "nominatim": {
                "enabled": True,
                "auth": "none",
                "use": "géocodage OpenStreetMap avec usage très modéré",
            },
        },
        "token_compression": {
            "api_results_compressed_by_default": True,
            "estimated_token_ratio": "approx chars/4",
            "modes": ["extractive", "hard"],
        },
    }
