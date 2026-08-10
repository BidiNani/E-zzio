import os
import sys
import subprocess
from tools.patch_pipeline import patch_pipeline

# Import sécurisé de l'index_api (si présent)
try:
    from tools.index_api import index_api
    HAS_INDEX = True
except ImportError:
    HAS_INDEX = False

class AutonomousGovernor:
    """
    Chef d'orchestre ReAct pour E-ZZIO.
    Expose une API de haut niveau, blindée et formatée pour l'IA (Gemini).
    """
    def __init__(self):
        self.max_retries = 3

    def search_codebase(self, query: str) -> str:
        """Outil IA : Cherche un fichier ou un contenu dans l'index SQLite."""
        if not HAS_INDEX:
            return "ERREUR: Index API non disponible."
        try:
            if "." in query and " " not in query:
                return index_api.search_file(query)
            return index_api.search_content(query)
        except Exception as e:
            return f"ERREUR RECHERCHE: {e}"

    def read_file(self, filepath: str) -> str:
        """Outil IA : Lit le contenu d'un fichier."""
        try:
            target = os.path.abspath(filepath)
            with open(target, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"ERREUR LECTURE: {e}"

    def write_patch(self, filepath: str, new_content: str) -> str:
        """Outil IA : Modifie un fichier via le pipeline sécurisé (auto-rollback)."""
        res = patch_pipeline.apply_patch(filepath, new_content)
        if res["success"]:
            return f"[SUCCES] {res['message']}"
        return f"[ECHEC PATCH] {res['error']}"

    def test_execution(self, filepath: str) -> str:
        """Outil IA : Exécute un script localement et capture le résultat (Sandbox)."""
        target = os.path.abspath(filepath)
        if not os.path.exists(target):
            return f"[ERREUR EXECUTION] Fichier introuvable : {filepath}"
        
        try:
            # Sécurité : Timeout de 10s pour éviter qu'une IA ne lance une boucle infinie
            result = subprocess.run(
                [sys.executable, target],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return f"[SUCCES EXECUTION]\n{result.stdout.strip()}"
            else:
                return f"[ERREUR EXECUTION]\n{result.stderr.strip()}"
        except subprocess.TimeoutExpired:
            return "[ERREUR EXECUTION] Timeout dépassé (10s). Le script contient une boucle infinie ou un blocage."
        except Exception as e:
            return f"[ERREUR SYSTEME CRITIQUE] {e}"

# Instance globale pour le serveur ReAct
governor = AutonomousGovernor()
