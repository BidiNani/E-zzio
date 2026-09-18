"""Endpoints REST de gestion des comptes connectés."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from core.accounts import store
from core.accounts.oauth_registry import list_providers, get_provider
from core.accounts.oauth_flow import build_authorize_url, exchange_code

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")

@router.get("/providers")
async def api_list_providers():
    providers = list_providers()
    connected = {a["provider"]: a for a in store.list_accounts()}
    for p in providers:
        acc = connected.get(p["id"])
        p["connected"] = acc is not None
        p["account"] = acc
    return {"ok": True, "providers": providers}

@router.get("/list")
async def api_list_accounts():
    return {"ok": True, "accounts": store.list_accounts()}

@router.post("/connect/{provider_id}")
async def api_connect(provider_id: str, request: Request):
    result = build_authorize_url(provider_id, _base_url(request))
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/callback/{provider_id}", response_class=HTMLResponse)
async def api_callback(provider_id: str, request: Request,
                       code: str = Query(...), state: str = Query(...)):
    result = await exchange_code(provider_id, code, state, _base_url(request))
    if not result.get("ok"):
        return HTMLResponse(
            f"""<html><body style="font-family:sans-serif;padding:40px;background:#0a0a0f;color:#f0f0f5">
            <h2>Connexion échouée</h2><pre>{result}</pre>
            <p><a href="http://localhost:1420" style="color:#4a9eff">Retour à E-zzio</a></p>
            </body></html>""", status_code=400)
    acc = result.get("account", {})
    name = acc.get("display_name") or acc.get("email") or provider_id
    return HTMLResponse(
        f"""<html><body style="font-family:sans-serif;padding:40px;background:#0a0a0f;color:#f0f0f5">
        <h2>Compte connecté</h2>
        <p><b>{provider_id}</b> - {name}</p>
        <p>Tu peux fermer cette fenêtre.</p>
        <script>setTimeout(()=>window.close(),1500)</script>
        </body></html>""")

@router.delete("/{provider_id}")
async def api_disconnect(provider_id: str):
    if not get_provider(provider_id):
        raise HTTPException(status_code=404, detail="Provider inconnu")
    removed = store.delete_account(provider_id)
    return {"ok": True, "removed": removed, "provider": provider_id}