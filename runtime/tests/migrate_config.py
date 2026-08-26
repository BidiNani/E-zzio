import re
import shutil
from pathlib import Path

root = Path("G:/AI/E-zzio")
f_google = root / "core/tool_gateway/google_bridge.py"
f_discord = root / "core/integrations/discord/discord_client.py"

# --- 0. CRÉATION DES BACKUPS ---
shutil.copy(f_google, f_google.with_suffix(".py.bak"))
shutil.copy(f_discord, f_discord.with_suffix(".py.bak"))

# --- 1. MIGRATION GOOGLE BRIDGE ---
c_google = f_google.read_text(encoding="utf-8")

# Suppression imports dotenv et injection du contrat
c_google = re.sub(r"from dotenv import load_dotenv\n", "", c_google)
c_google = re.sub(r"(import hmac\n)", r"\1from contracts.config_port import IConfigProvider\n", c_google)

# Suppression du chemin en dur ENV_PATH et de l'appel load_dotenv()
c_google = re.sub(r"ENV_PATH = ROOT_DIR / \"secrets\" / \".env\"\n*", "", c_google)
c_google = re.sub(r"load_dotenv\(dotenv_path=ENV_PATH, override=True\)\n*", "", c_google)

# Modification de la signature du constructeur
c_google = c_google.replace("def __init__(self):", "def __init__(self, config: IConfigProvider):")

# Remplacement de os.getenv par config.require (fail-fast)
pattern_secret = r'secret = os\.getenv\("EZZIO_LEDGER_SECRET"\)\n\s*if not secret:\n\s*raise ValueError\("CRITICAL_SECURITY_ERROR: EZZIO_LEDGER_SECRET is required for the Vault."\)'
c_google = re.sub(pattern_secret, 'secret = config.require("EZZIO_LEDGER_SECRET")', c_google)

# Nettoyage de l'instance globale potentiellement présente en bas de fichier
c_google = re.sub(r"^google_bridge\s*=\s*GoogleIdentityBridge\(\)\s*$", "", c_google, flags=re.MULTILINE)

f_google.write_text(c_google, encoding="utf-8")
print(f"[OK] {f_google.name} refactorisé (Purifié de l'infrastructure).")


# --- 2. MIGRATION DISCORD CLIENT (COMPOSITION ROOT) ---
c_discord = f_discord.read_text(encoding="utf-8")

# Modification de l'import (On importe la classe et l'adaptateur DotEnv)
c_discord = c_discord.replace(
    "from core.tool_gateway.google_bridge import google_bridge",
    "from core.tool_gateway.google_bridge import GoogleIdentityBridge\nfrom runtime.adapters.config.dotenv_provider import DotEnvConfigProvider",
)

# Injection de l'instanciation (Wiring) juste avant OWNER_ID
injection = """config = DotEnvConfigProvider(env_path=str(PROJECT_ROOT / "secrets" / ".env"))
google_bridge = GoogleIdentityBridge(config=config)

OWNER_ID"""
c_discord = c_discord.replace("OWNER_ID", injection, 1)

# Remplacement de os.getenv par config.get sur le réseau
c_discord = c_discord.replace('os.getenv("DISCORD_BOT_TOKEN")', 'config.get("DISCORD_BOT_TOKEN")')
c_discord = c_discord.replace('os.getenv("DISCORD_TOKEN")', 'config.get("DISCORD_TOKEN")')
c_discord = c_discord.replace('os.getenv("EZZIO_LOCAL_API_URL"', 'config.get("EZZIO_LOCAL_API_URL"')

f_discord.write_text(c_discord, encoding="utf-8")
print(f"[OK] {f_discord.name} refactorisé (Devenu Point d'Assemblage).")

print("\n[SUCCÈS] Migration terminée ! Des sauvegardes (.py.bak) garantissent le retour en arrière.")
