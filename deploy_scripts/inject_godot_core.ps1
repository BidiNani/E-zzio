# ==============================================================================
# E-ZZIO GODOT 4 CORE INJECTION & RESTART (.PS1)
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectPath = "G:\AI\E-zzio"
$WebServerPath = Join-Path $ProjectPath "web_server.py"

Write-Host "[..] Mise à jour de web_server.py avec le profil expert Godot 4..." -ForegroundColor Yellow

$ServerCode = @'
# ==============================================================================
# E-ZZIO SOVEREIGN MASTER CORE (GODOT 4 EXPERT EDITION)
# ==============================================================================

import os
import pathlib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv
import file_tools

PROJECT_ROOT = pathlib.Path(r"G:\AI\E-zzio")
load_dotenv(PROJECT_ROOT / "omnipresence.env", override=True)
if not os.getenv("GEMINI_API_KEY"):
    load_dotenv(PROJECT_ROOT / "secrets" / "omnipresence.env", override=True)
if not os.getenv("GEMINI_API_KEY"):
    load_dotenv(PROJECT_ROOT / "secrets" / ".env", override=True)

client = genai.Client()
app = FastAPI(title="E-zzio Sovereign Master Core", version="4.7.0")

GODOT_EXPERT_PROMPT = """
Tu es E-zzio, l'intelligence souveraine et le collaborateur technique de l'utilisateur. 
Tu possèdes une expertise de pointe absolue sur **Godot 4** et GDScript 2.0 pour la conception et le développement de jeux mobiles cross-platform.
Directives permanentes et strictes :
- Utilise rigoureusement le typage statique et explicite en GDScript 2.0.
- Emploie les annotations modernes de Godot 4 (@export, @onready, @export_category, @rpc, etc.).
- Structure les architectures de jeux en composants et scènes modulaires, propres et maintenables.
- Intègre nativement la gestion des résolutions adaptatives, des contrôles tactiles fluides et des performances mobiles.
- Tu disposes d'outils d'accès aux fichiers et de scan du lecteur G: via le Function Calling. Utilise-les activement pour lire, analyser, écrire ou corriger les scripts du projet de l'utilisateur.
"""

class ChatRequest(BaseModel):
    user_id: str
    text: str
    image_url: str | None = None
    autoriser_outils_locaux: bool = True

@app.get("/health")
def health_check():
    return {"status": "online", "core": "E-zzio Sovereign Master", "godot_expert_active": True}

@app.post("/master/chat")
async def master_chat(req: ChatRequest):
    try:
        contents = []
        
        if req.image_url:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(req.image_url) as resp:
                    if resp.status == 200:
                        img_bytes = await resp.read()
                        contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
        
        contents.append(req.text)
        
        config = types.GenerateContentConfig(
            system_instruction=GODOT_EXPERT_PROMPT,
            temperature=0.3,
            tools=[file_tools.DECLARATIONS_OUTILS]
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=contents,
            config=config
        )
        
        if response.function_calls:
            function_responses = []
            for fc in response.function_calls:
                tool_name = fc.name
                tool_args = fc.args
                tool_result = file_tools.executer_appel_outil(tool_name, tool_args)
                function_responses.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"result": tool_result}
                    )
                )
            
            contents.append(response.candidates[0].content)
            contents.extend(function_responses)
            
            final_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=contents,
                config=config
            )
            reply_text = final_response.text
        else:
            reply_text = response.text if response.text else "Réponse vide générée par le noyau."
            
        return {"response": reply_text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
'@

Set-Content -LiteralPath $WebServerPath -Value $ServerCode -Encoding UTF8
Write-Host "[OK] web_server.py mis à jour avec le profil Godot 4." -ForegroundColor Green

Write-Host "[..] Redémarrage des processus en arrière-plan..." -ForegroundColor Yellow
Set-Location $ProjectPath

Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { 
    $_.CommandLine -like "*web_server.py*" -or $_.CommandLine -like "*discord_agent_v2.py*" 
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

try {
    $conn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
    if ($conn) { Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue }
} catch {}

& "$ProjectPath\Start-EzzioBackground.ps1"