# ==============================================================================
# E-ZZIO DEPLOY FIX (.PS1)
# Deploie web_server.py et file_tools.py corriges, cree tools/, redemarre.
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectPath = "G:\AI\E-zzio"
$ToolsPath = Join-Path $ProjectPath "tools"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " DEPLOIEMENT DES CORRECTIFS E-ZZIO" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Arret des process en cours
Write-Host "[..] Arret des services en cours..." -ForegroundColor Yellow
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object {
    $_.CommandLine -like "*web_server.py*" -or $_.CommandLine -like "*discord_agent_v2.py*"
} | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

try {
    $conn = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
    if ($conn) { Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue }
} catch {}

# 2. Sauvegarde des anciens fichiers avant ecrasement
Write-Host "[..] Sauvegarde des anciens fichiers (.bak)..." -ForegroundColor Yellow
foreach ($f in @("web_server.py", "file_tools.py")) {
    $src = Join-Path $ProjectPath $f
    if (Test-Path $src) {
        Copy-Item -LiteralPath $src -Destination "$src.bak" -Force
    }
}

# 3. Ecriture de web_server.py corrige
Write-Host "[..] Deploiement de web_server.py..." -ForegroundColor Yellow
$WebServerCode = @'
# ==============================================================================
# E-ZZIO SOVEREIGN MASTER CORE (MULTI-SOURCE SEARCH & GODOT EXPERT)
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
app = FastAPI(title="E-zzio Sovereign Master Core", version="4.8.0")

MASTER_SYSTEM_PROMPT = """
Tu es E-zzio, l'intelligence souveraine et le collaborateur technique de l'utilisateur.
Tu possèdes une double expertise absolue :
1. **Godot 4 & GDScript 2.0** : Typage strict, annotations modernes (@export, @onready), architecture modulaire et optimisation mobile cross-platform.
2. **Recherche & Analyse Multi-Sources** : Lorsque tu effectues des recherches sur le web, tu agis comme un moteur d'agrégation de pointe (type Perplexity/ChatGPT). Tu croises les sources, vérifies la cohérence technique, cites les tendances et évites les biais superficiels.

Directives strictes :
- Utilise l'outil de recherche Google (Grounding) dès qu'une information technique, une documentation à jour ou une actualité est nécessaire.
- Structure tes synthèses avec clarté, précision et concision.
- Tu disposes d'outils locaux sur le lecteur G: (via file_tools) et de génération multimédia. Utilise-les dès que l'action est requise.
"""

class ChatRequest(BaseModel):
    user_id: str
    text: str
    image_url: str | None = None
    autoriser_outils_locaux: bool = True

@app.get("/health")
def health_check():
    return {"status": "online", "core": "E-zzio Sovereign Master", "web_grounding_active": True}

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
        
        # Configuration combinant les outils locaux et le Grounding Google Search natif
        config = types.GenerateContentConfig(
            system_instruction=MASTER_SYSTEM_PROMPT,
            temperature=0.2,
            tools=[
                file_tools.DECLARATIONS_OUTILS,
                types.Tool(google_search=types.GoogleSearch())
            ]
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
Set-Content -LiteralPath (Join-Path $ProjectPath "web_server.py") -Value $WebServerCode -Encoding UTF8

# 4. Ecriture de file_tools.py corrige
Write-Host "[..] Deploiement de file_tools.py..." -ForegroundColor Yellow
$FileToolsCode = @'
# ==============================================================================
# E-ZZIO DYNAMIC G-DRIVE TOOL REGISTRY & MEDIA GENERATOR (VERSION DURCIE)
# ==============================================================================

import os
import pathlib
import shlex
import subprocess
from google import genai
from google.genai import types

G_DRIVE_ROOT = pathlib.Path("G:\\AI")
PROJECT_ROOT = (G_DRIVE_ROOT / "E-zzio").resolve()
GENERATED_DIR = PROJECT_ROOT / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

# --- Confinement ---------------------------------------------------------
# Toute lecture/écriture de fichier est restreinte à ce dossier. Un chemin
# qui résout en dehors (via .., un chemin absolu ailleurs, un lien
# symbolique, etc.) est rejeté.
SAFE_ROOT = PROJECT_ROOT

# Seuls les scripts placés ici sont exposés à l'IA comme "outils" exécutables.
# (Auparavant : tout G:\AI, y compris backups/anciens scripts non prévus
# pour une exécution automatisée.)
TOOLS_ROOT = PROJECT_ROOT / "tools"
TOOLS_ROOT.mkdir(parents=True, exist_ok=True)

PYTHON_EXE = "G:\\Python312\\python.exe"
POWERSHELL_EXE = "powershell.exe"

client = genai.Client()


def _resolve_safe_path(chemin: str) -> pathlib.Path:
    """Résout `chemin` (relatif ou absolu) et vérifie qu'il reste sous
    SAFE_ROOT. Lève ValueError sinon."""
    p = pathlib.Path(chemin)
    candidate = p if p.is_absolute() else (SAFE_ROOT / p)
    resolved = candidate.resolve()
    try:
        resolved.relative_to(SAFE_ROOT)
    except ValueError:
        raise ValueError(
            f"Chemin refusé (hors de {SAFE_ROOT}) : {chemin}"
        )
    return resolved


def discover_g_drive_tools():
    """N'indexe que les scripts placés explicitement dans TOOLS_ROOT,
    pas l'ensemble du lecteur G:."""
    tools_index = {}
    if not TOOLS_ROOT.exists():
        return tools_index
    for path in TOOLS_ROOT.glob("**/*"):
        if path.is_file() and path.suffix in [".py", ".ps1"]:
            if "venv" in path.parts or ".git" in path.parts or "archive" in path.parts:
                continue
            tool_name = f"{path.parent.name}_{path.stem}"
            tools_index[tool_name] = str(path.resolve())
    return tools_index


DECLARATIONS_OUTILS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="lister_outils_g_drive",
            description="Liste les scripts et outils disponibles dans le dossier tools/ du projet E-zzio.",
            parameters=types.Schema(type=types.Type.OBJECT, properties={}),
        ),
        types.FunctionDeclaration(
            name="executer_outil_g_drive",
            description="Exécute un script répertorié dans tools/.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "nom_outil": types.Schema(type=types.Type.STRING, description="Identifiant de l'outil."),
                    "arguments": types.Schema(type=types.Type.STRING, description="Arguments optionnels (séparés par des espaces).")
                },
                required=["nom_outil"]
            ),
        ),
        types.FunctionDeclaration(
            name="generer_image",
            description="Génère une image à partir d'une description textuelle (Prompt) via Imagen et l'enregistre localement.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "prompt": types.Schema(type=types.Type.STRING, description="Description détaillée de l'image à générer.")
                },
                required=["prompt"]
            ),
        ),
        types.FunctionDeclaration(
            name="lire_fichier_local",
            description="Lit le contenu textuel d'un fichier du projet E-zzio.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "chemin": types.Schema(type=types.Type.STRING, description="Chemin du fichier (relatif au projet, ou absolu à l'intérieur du projet).")
                },
                required=["chemin"]
            ),
        ),
        types.FunctionDeclaration(
            name="ecrire_fichier_local",
            description="Écrit ou met à jour un fichier du projet E-zzio.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "chemin": types.Schema(type=types.Type.STRING, description="Chemin du fichier (relatif au projet, ou absolu à l'intérieur du projet)."),
                    "contenu": types.Schema(type=types.Type.STRING, description="Contenu textuel.")
                },
                required=["chemin", "contenu"]
            ),
        )
    ]
)


def executer_appel_outil(nom: str, args: dict) -> str:
    try:
        if nom == "lister_outils_g_drive":
            tools = discover_g_drive_tools()
            return f"Outils détectés dans tools/ ({len(tools)}) :\n" + "\n".join(
                [f"- {k}: {v}" for k, v in list(tools.items())[:30]]
            )

        elif nom == "executer_outil_g_drive":
            tools = discover_g_drive_tools()
            tool_name = args.get("nom_outil")
            extra_args_str = args.get("arguments", "")
            if tool_name not in tools:
                return f"Erreur : L'outil '{tool_name}' est introuvable dans tools/."
            script_path = tools[tool_name]
            ext = pathlib.Path(script_path).suffix

            # Arguments passés comme une VRAIE liste, jamais interpolés dans
            # une chaîne shell : élimine l'injection de commande.
            try:
                extra_args = shlex.split(extra_args_str) if extra_args_str else []
            except ValueError as e:
                return f"Erreur : arguments invalides ({e})."

            if ext == ".py":
                cmd = [PYTHON_EXE, script_path, *extra_args]
            else:
                cmd = [POWERSHELL_EXE, "-ExecutionPolicy", "Bypass", "-File", script_path, *extra_args]

            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, timeout=30)
            output = result.stdout[:4000] if result.stdout else "Exécution réussie sans sortie texte."
            return output if result.returncode == 0 else f"[ÉCHEC - CODE {result.returncode}]\n{result.stderr[:2000]}"

        elif nom == "generer_image":
            prompt = args.get("prompt")
            result = client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=prompt,
                config=types.GenerateImagesConfig(number_of_images=1, output_mime_type="image/jpeg")
            )
            for generated_image in result.generated_images:
                file_path = GENERATED_DIR / f"image_gen_{os.urandom(4).hex()}.jpg"
                with open(file_path, "wb") as f:
                    f.write(generated_image.image.image_bytes)
                return f"Image générée avec succès et enregistrée sous : {file_path}"
            return "Échec de la génération de l'image."

        elif nom == "lire_fichier_local":
            chemin = args.get("chemin")
            try:
                p = _resolve_safe_path(chemin)
            except ValueError as e:
                return f"Erreur : {e}"
            return p.read_text(encoding="utf-8")[:4000] if p.exists() else f"Introuvable : {chemin}"

        elif nom == "ecrire_fichier_local":
            chemin = args.get("chemin")
            contenu = args.get("contenu")
            try:
                p = _resolve_safe_path(chemin)
            except ValueError as e:
                return f"Erreur : {e}"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(contenu, encoding="utf-8")
            return f"Écriture réussie : {p}"

        else:
            return f"Outil inconnu : {nom}"

    except Exception as e:
        return f"Erreur critique lors de l'exécution de l'outil {nom} : {str(e)}"

'@
Set-Content -LiteralPath (Join-Path $ProjectPath "file_tools.py") -Value $FileToolsCode -Encoding UTF8

# 5. Creation du dossier tools/ (perimetre des scripts executables par l'IA)
if (-not (Test-Path $ToolsPath)) {
    Write-Host "[..] Creation de $ToolsPath ..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $ToolsPath -Force | Out-Null
    Write-Host "[!] tools/ est vide : deplaces-y les scripts que tu veux rendre executables par E-zzio." -ForegroundColor Red
} else {
    Write-Host "[OK] tools/ existe deja." -ForegroundColor Green
}

Write-Host "[OK] Fichiers deployes avec succes." -ForegroundColor Green

# 6. Redemarrage des services
Write-Host "[..] Redemarrage des services E-zzio..." -ForegroundColor Yellow
& (Join-Path $ProjectPath "Start-EzzioBackground.ps1")

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " DEPLOIEMENT TERMINE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
