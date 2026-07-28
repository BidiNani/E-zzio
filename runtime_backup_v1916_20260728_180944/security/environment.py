import os
import tempfile

class EnvironmentSanitizer:
    """Purge l'environnement de toute variable sensible (Tokens, Credentials, PATH complet)."""
    
    @staticmethod
    def get_safe_env() -> dict:
        safe_env = {}
        
        # 1. Conservation vitale Windows uniquement
        for k in ["SYSTEMROOT", "COMSPEC", "WINDIR"]:
            if k in os.environ:
                safe_env[k] = os.environ[k]
        
        # 2. PATH Strict et Minimaliste
        ps_path = r"C:\Windows\System32\WindowsPowerShell\v1.0"
        sys32_path = r"C:\Windows\System32"
        safe_env["PATH"] = f"{ps_path};{sys32_path}"
        
        # 3. Répertoires temporaires sandboxés
        safe_env["TEMP"] = tempfile.gettempdir()
        safe_env["TMP"] = safe_env["TEMP"]
        
        # 4. Indicateurs virtuels
        safe_env["EZZIO_RUNTIME"] = "1"
        safe_env["POWERSHELL_TELEMETRY_OPTOUT"] = "1"
        
        return safe_env