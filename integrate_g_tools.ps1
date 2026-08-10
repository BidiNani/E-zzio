# ==============================================================================
# E-ZZIO G-DRIVE TOOLS INTEGRATION AUTOMATION (.PS1)
# ==============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectPath = "G:\AI\E-zzio"
$FileToolsPath = Join-Path $ProjectPath "file_tools.py"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " INTÉGRATION UNIFIÉE DES OUTILS DU LECTEUR G:" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Mise à jour de file_tools.py avec un scanner dynamique du lecteur G:
$FileToolsCode = @'
# ==============================================================================
# E-ZZIO DYNAMIC G-DRIVE TOOL REGISTRY & EXECUTOR
# ==============================================================================

import os
import pathlib
import subprocess
import glob
from google.genai import types

G_DRIVE_ROOT = pathlib.Path("G:\\AI")

def discover_g_drive_tools():
    """Scanne récursivement le lecteur G: pour lister les scripts exécutables."""
    tools_index = {}
    if not G_DRIVE_ROOT.exists():
        return tools_index
        
    # Recherche de tous les scripts .py et .ps1 dans l'arborescence G:\AI
    for path in G_DRIVE_ROOT.glob("**/*"):
        if path.is_file() and path.suffix in [".py", ".ps1"]:
            # Exclure les environnements virtuels ou archives
            if "venv" in path.parts or ".git" in path.parts or "archive" in path.parts:
                continue
            tool_name = f"{path.parent.name}_{path.stem}"
            tools_index[tool_name] = str(path.resolve())
            
    return tools_index

# Déclaration dynamique pour le Function Calling Gemini
DECLARATIONS_OUTILS = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="lister_outils_g_drive",
            description="Liste tous les scripts et outils disponibles sur l'ensemble du lecteur G:.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
            ),
        ),
        types.FunctionDeclaration(
            name="executer_outil_g_drive",
            description="Exécute un script ou un outil répertorié sur le lecteur G: par son nom identifiant.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "nom_outil": types.Schema(
                        type=types.Type.STRING,
                        description="L'identifiant de l'outil (ex: Bidi_Intelligence_Platform_main)."
                    ),
                    "arguments": types.Schema(
                        type=types.Type.STRING,
                        description="Arguments optionnels à passer au script."
                    )
                },
                required=["nom_outil"]
            ),
        ),
        types.FunctionDeclaration(
            name="lire_fichier_local",
            description="Lit le contenu textuel d'un fichier sur le disque hôte.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "chemin": types.Schema(
                        type=types.Type.STRING,
                        description="Chemin absolu ou relatif du fichier."
                    )
                },
                required=["chemin"]
            ),
        ),
        types.FunctionDeclaration(
            name="ecrire_fichier_local",
            description="Écrit ou met à jour un fichier sur le disque hôte.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "chemin": types.Schema(
                        type=types.Type.STRING,
                        description="Chemin du fichier à écrire."
                    ),
                    "contenu": types.Schema(
                        type=types.Type.STRING,
                        description="Contenu textuel complet."
                    )
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
            return f"Outils G: détectés ({len(tools)}) :\n" + "\n".join([f"- {k}: {v}" for k, v in list(tools.items())[:30]])
            
        elif nom == "executer_outil_g_drive":
            tools = discover_g_drive_tools()
            tool_name = args.get("nom_outil")
            extra_args = args.get("arguments", "")
            
            if tool_name not in tools:
                return f"Erreur : L'outil '{tool_name}' est introuvable dans l'index G:."
                
            script_path = tools[tool_name]
            ext = pathlib.Path(script_path).suffix
            
            if ext == ".py":
                cmd = f"G:\\Python312\\python.exe \"{script_path}\" {extra_args}"
            elif ext == ".ps1":
                cmd = f"powershell.exe -ExecutionPolicy Bypass -File \"{script_path}\" {extra_args}"
            else:
                return f"Erreur : Type de fichier non exécutable ({ext})."
                
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True, timeout=30)
            output = result.stdout if result.returncode == 0 else f"Erreur d'exécution :\n{result.stderr}"
            return output[:3000]
            
        elif nom == "lire_fichier_local":
            chemin = args.get("chemin")
            p = pathlib.Path(chemin)
            if not p.is_absolute():
                p = G_DRIVE_ROOT / "E-zzio" / p
            if p.exists() and p.is_file():
                return p.read_text(encoding="utf-8")[:4000]
            return f"Fichier introuvable : {chemin}"
            
        elif nom == "ecrire_fichier_local":
            chemin = args.get("chemin")
            contenu = args.get("contenu")
            p = pathlib.Path(chemin)
            if not p.is_absolute():
                p = G_DRIVE_ROOT / "E-zzio" / p
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(contenu, encoding="utf-8")
            return f"Succès de l'écriture : {p}"
            
        else:
            return f"Outil inconnu : {nom}"
            
    except Exception as e:
        return f"Erreur critique lors de l'exécution de l'outil {nom} : {str(e)}"
'@

Set-Content -LiteralPath $FileToolsPath -Value $FileToolsCode -Encoding UTF8
Write-Host "[OK] Fichier file_tools.py mis à jour avec le registre G-Drive global." -ForegroundColor Green

# 2. Redémarrage des processus en arrière-plan via le démon stable
Write-Host "[..] Redémarrage des services E-zzio..." -ForegroundColor Yellow
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