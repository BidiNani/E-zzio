"""
[DEPRECATED] Ce fichier importe un module runtime.* supprime (archive 2026-09-18).
A migrer ou supprimer. Ne pas utiliser en production.
"""

from pathlib import Path

print("[*] Application des contrats ExternalExecutorBase...")

for path_str in ["runtime/tools/executors/powershell.py", "runtime/tools/executors/filesystem.py"]:
    p = Path(path_str)
    if p.exists():
        code = p.read_text(encoding="utf-8")

        # Ajout de l'héritage si absent
        if "class PowerShellExecutor:" in code:
            code = code.replace("class PowerShellExecutor:", "class PowerShellExecutor(ExternalExecutorBase):")
        elif "class FileSystemExecutor:" in code:
            code = code.replace("class FileSystemExecutor:", "class FileSystemExecutor(ExternalExecutorBase):")

        # Import de la base si absent
        if "ExternalExecutorBase" not in code:
            import_target = "from runtime.tools.tool_schema import ToolResult"
            if import_target in code:
                code = code.replace(import_target, f"{import_target}\nfrom runtime.external.base import ExternalExecutorBase")
            else:
                code = "from runtime.external.base import ExternalExecutorBase\n" + code

        p.write_text(code, encoding="utf-8")
        print(f"[+] Contrat restauré pour {path_str}")

print("[OK] Restauration des exécuteurs terminée.")
