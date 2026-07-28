from pathlib import Path
import importlib
import sys

print("=== INSPECTION DES ROUTES TOOL REGISTRY ===")

# Tentative d'import du registre d'outils ou d'actions
try:
    from runtime.tools.pipeline import ToolPipeline
    print("[+] ToolPipeline trouvé.")
except Exception as e:
    print("[-] ToolPipeline non chargé directement:", e)

try:
    from runtime.action.registry import ActionRegistry
    reg = ActionRegistry()
    print("\n--- ActionRegistry._contracts ---")
    for name in reg._contracts:
        if any(k in name.lower() for k in ['power', 'file', 'shell']):
            print(f"Action: {name}")
except Exception as e:
    print("[-] ActionRegistry non inspectable ainsi:", e)

# Recherche textuelle des enregistrements de system.powershell et filesystem.read dans tout le code source
print("\n--- Recherche des occurrences d'enregistrement ---")
for p in Path("runtime").rglob("*.py"):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if "system.powershell" in txt or "filesystem.read" in txt or "powershell.safe.execute" in txt:
        print(f"Fichier suspect : {p}")
        for line in txt.splitlines():
            if any(k in line for k in ["system.powershell", "filesystem.read", "powershell.safe.execute", "register"]):
                print(f"   -> {line.strip()}")
