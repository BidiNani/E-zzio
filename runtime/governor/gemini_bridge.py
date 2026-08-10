import os
from runtime.governor.controller import governor

# Import sécurisé (évite le crash si le module n'est pas dans l'environnement)
try:
    import google.generativeai as genai
    HAS_GEMINI_SDK = True
except ImportError:
    HAS_GEMINI_SDK = False

class GeminiAutonomousLoop:
    """
    Pont de connexion entre le Governor E-ZZIO et l'API Gemini.
    Implémente le Function Calling Automatique (Boucle ReAct gérée par le SDK).
    """
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model = None
        self.chat_session = None
        
        if HAS_GEMINI_SDK and self.api_key:
            genai.configure(api_key=self.api_key)
            self._init_model()

    def _init_model(self):
        """Déclare les outils avec Type Hints et Docstrings stricts pour le JSON Schema de Gemini."""
        
        def search_codebase(query: str) -> str:
            """Outil IA : Cherche un fichier ou un contenu dans l'index SQLite E-ZZIO."""
            return governor.search_codebase(query)

        def read_file(filepath: str) -> str:
            """Outil IA : Lit le contenu brut d'un fichier local."""
            return governor.read_file(filepath)

        def write_patch(filepath: str, new_content: str) -> str:
            """Outil IA : Modifie un fichier. Protection anti-corruption et rollback inclus."""
            return governor.write_patch(filepath, new_content)

        def test_execution(filepath: str) -> str:
            """Outil IA : Exécute un script localement et retourne la console (Sandbox)."""
            return governor.test_execution(filepath)

        self.tools = [search_codebase, read_file, write_patch, test_execution]
        
        instruction = (
            "Tu es E-ZZIO, une IA autonome et un ingénieur système de classe industrielle. "
            "Tu as un accès direct au système de fichiers de ton propre code source via tes outils. "
            "Règle d'or : Quand on te demande une modification, utilise toujours search_codebase, "
            "puis read_file, puis write_patch, et valide toujours ton travail avec test_execution."
        )

        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            tools=self.tools,
            system_instruction=instruction
        )
        # Activation de la boucle ReAct automatique
        self.chat_session = self.model.start_chat(enable_automatic_function_calling=True)

    def run_task(self, prompt: str) -> str:
        """Envoie l'ordre à l'IA. Elle va utiliser ses outils de manière autonome avant de répondre."""
        if not HAS_GEMINI_SDK:
            return "[!] ERREUR: SDK google.generativeai introuvable dans l'environnement Python."
        if not self.model:
            return "[!] ERREUR: Clé API Gemini manquante. Renseignez GEMINI_API_KEY."
            
        try:
            response = self.chat_session.send_message(prompt)
            return response.text
        except Exception as e:
            return f"[!] ERREUR CRITIQUE GEMINI LOOP: {str(e)}"

# Instance prête à être utilisée par Discord ou le WebServer
autonomous_agent = GeminiAutonomousLoop()
