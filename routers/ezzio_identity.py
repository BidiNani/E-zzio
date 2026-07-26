from fastapi import APIRouter, Request

from core.ezzio_identity import (
    identity_payload,
    manifest_payload,
    policy_payload,
    routes_payload,
)

router = APIRouter(prefix="/ezzio", tags=["ezzio"])

@router.get("/identity")
async def ezzio_identity():
    return identity_payload()

@router.get("/manifest")
async def ezzio_manifest():
    return manifest_payload()

@router.get("/policy")
async def ezzio_policy():
    return policy_payload()

@router.get("/routes")
async def ezzio_routes(request: Request):
    return routes_payload(request.app)
