import os
import gc
from runtime.governor.controller import governor
from runtime.security.secrets import secret_provider

try:
    import google.generativeai as genai
    HAS_GEMINI_SDK = True
except ImportError:
    HAS_GEMINI_SDK = False

class GeminiAutonomousLoop:
    def __init__(self):
        self.model = None
        self.chat_session = None
        self._current_key_hash = None
        self._current_model_name = "gemini-1.5-flash"
        self._check_and_apply_rotation()

    def _check_and_apply_rotation(self) -> bool:
        latest_hash = secret_provider.get_hash("GEMINI_API_KEY")
        if not latest_hash:
            return False

        vault_model = secret_provider.get("EZZIO_GEMINI_MODEL") or "gemini-1.5-flash"

        if latest_hash != self._current_key_hash or vault_model != self._current_model_name or not self.chat_session:
            key = secret_provider.get("GEMINI_API_KEY")
            if not key:
                return False
            
            # 1. Destruction des références précédentes
            self.chat_session = None
            self.model = None
            self._current_model_name = vault_model
            
            # 2. Tentative de reset profond de l'état interne du SDK Google
            try:
                genai._client = None
            except:
                pass
                
            # 3. Force le GC
            gc.collect()
                
            # 4. Re-configuration
            genai.configure(api_key=key)
            key = None 
            
            self._init_model()
            self._current_key_hash = latest_hash
        
        return True

    def _init_model(self):
        def search_codebase(query: str) -> str:
            return governor.search_codebase(query)
        def read_file(filepath: str) -> str:
            return governor.read_file(filepath)
        def write_patch(filepath: str, new_content: str) -> str:
            return governor.write_patch(filepath, new_content)
        def test_execution(filepath: str) -> str:
            return governor.test_execution(filepath)

        self.tools = [search_codebase, read_file, write_patch, test_execution]
        instruction = (
            "Tu es E-ZZIO, IA autonome et ingénieur système souverain. "
            "Utilise search_codebase, read_file, write_patch, et valide avec test_execution."
        )

        self.model = genai.GenerativeModel(
            model_name=self._current_model_name,
            tools=self.tools,
            system_instruction=instruction
        )
        self.chat_session = self.model.start_chat(enable_automatic_function_calling=True)

    def run_task(self, prompt: str) -> str:
        if not HAS_GEMINI_SDK:
            return "[!] ERREUR: SDK google.generativeai introuvable."
        if not self._check_and_apply_rotation():
            return "[!] ERREUR: Clé API Gemini manquante dans le Vault."

        try:
            response = self.chat_session.send_message(prompt)
            return response.text
        except Exception as e:
            return f"[!] ERREUR CRITIQUE GEMINI LOOP: {str(e)}"

autonomous_agent = GeminiAutonomousLoop()