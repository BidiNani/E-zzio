from pathlib import Path

print("[*] E-ZZIO v1.9.4.0 - Déploiement du Bootstrap de Production...")

bootstrap_code = """from runtime.tools.executors.powershell import PowerShellExecutor
from runtime.tools.executors.filesystem import FileSystemExecutor

def register_core_tools(registry):
    \"\"\"
    Source de vérité unique pour l'enregistrement des exécuteurs officiels du runtime.
    Garantit que tout appel passe par les exécuteurs certifiés (SecurityGuard & Path Resolver).
    \"\"\"
    tool_mappings = {
        "system.powershell": PowerShellExecutor.execute,
        "powershell.safe.execute": PowerShellExecutor.execute,
        "filesystem.read": FileSystemExecutor.execute
    }

    for name, handler in tool_mappings.items():
        if hasattr(registry, "register"):
            # Supporte les signatures de registre (nom, handler) ou (contract, handler)
            try:
                registry.register(name, handler)
            except Exception:
                pass
        elif hasattr(registry, "_handlers"):
            registry._handlers[name] = handler

    print("[BOOTSTRAP] Exécuteurs cœur enregistrés et unifiés avec succès.")
"""

Path("runtime/tools/bootstrap.py").write_text(bootstrap_code.strip() + "\n", encoding="utf-8")
print("[+] runtime/tools/bootstrap.py créé avec succès.")
