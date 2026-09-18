"""E-ZZIO — télémétrie agents : SSE + vue mobile."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, StreamingResponse

router = APIRouter(prefix="/api/v1/telemetry", tags=["telemetry"])

AGENT_VIEW_HTML = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>E-ZZIO Agent View</title>
<style>
body{font-family:system-ui;background:#0b0e14;color:#e6e6e6;margin:0;padding:8px}
h1{font-size:1.1em}.node{border:1px solid #333;border-radius:8px;margin:6px 0;padding:6px 8px}
.badge{display:inline-block;padding:1px 8px;border-radius:10px;font-size:.8em}
.RUNNING{background:#5a4a00;animation:pl 1s infinite alternate}
@keyframes pl{from{opacity:1}to{opacity:.4}}
.SUCCESS{background:#0a4d1f}.FAILED{background:#5a1111}.PENDING{background:#333}.BLOCKED{background:#4d2a0a}
.TOOL{background:#0a2a4d}details{margin-top:4px}summary{cursor:pointer;color:#9cf}
.meta{color:#888;font-size:.75em}
</style></head><body>
<h1>🤖 E-ZZIO Agent View</h1>
<div id="t">connexion…</div>
<script>
const box=document.getElementById('t');const nodes={};
const es=new EventSource('/api/v1/telemetry/stream'+location.search);
es.onmessage=e=>{try{const ev=JSON.parse(e.data);upsert(ev);}catch(_){}};
function upsert(ev){
 const id=ev.agent_id+(ev.tool_name?':'+ev.tool_name:'');
 let d=nodes[id];
 if(!d){d=document.createElement('details');d.open=true;box.prepend(d);nodes[id]=d;}
 const badge=ev.event_type==='TOOL_CALL'||ev.event_type==='TOOL_RESULT'?'TOOL':ev.status;
 d.innerHTML=`<summary><span class="badge ${badge}">${ev.status}</span> <b>${id}</b> <span class="meta">${ev.event_type} · ${ev.duration_ms??'-'} ms · ${new Date(ev.timestamp*1000).toLocaleTimeString()}</span></summary><div class="meta">${(ev.payload&&ev.payload.value||JSON.stringify(ev.payload||{}))}</div>`;
};
es.onerror=()=>{box.innerHTML='⚠️ flux coupé — <a href="" style="color:#9cf">reconnecter</a>';es.close();};
</script></body></html>
"""


@router.get("/agent-view", response_class=HTMLResponse)
async def agent_view():
    return AGENT_VIEW_HTML


@router.get("/stream")
async def telemetry_stream(trace_id: str = Query(default="")):
    from core.telemetry.agent_tracer import tracer

    async def gen():
        q = tracer.subscribe(trace_id or None)
        try:
            while True:
                try:
                    ev = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"data: {ev.model_dump_json()}\n\n"
                except TimeoutError:
                    yield ": ping\n\n"
        finally:
            tracer.unsubscribe(q)

    return StreamingResponse(
        gen(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                 "X-Accel-Buffering": "no"},
    )
