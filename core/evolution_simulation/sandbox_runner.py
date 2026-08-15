"""
E-ZZIO V7.35 — Sandbox Runner
Exécute un code candidat dans un environnement isolé pour mesurer ses performances empiriques.
"""
import time
import sys
import io
import traceback

class SandboxRunner:
    @staticmethod
    def execute_in_sandbox(code_content: str, test_inputs: list = None, timeout_seconds: float = 2.0) -> dict:
        test_inputs = test_inputs or []
        local_scope = {}
        
        start_time = time.perf_counter()
        try:
            # Capture de la sortie standard pour éviter toute pollution
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            # Compilation et exécution sécurisée dans un espace restreint
            compiled_code = compile(code_content, "<string>", "exec")
            
            # Exécution avec limite de temps conceptuelle (mesure de la durée)
            exec(compiled_code, {"__builtins__": {"range": range, "len": len, "int": int, "float": float, "str": str}}, local_scope)
            
            execution_time = time.perf_counter() - start_time
            sys.stdout = old_stdout

            return {
                "success": True,
                "execution_time_seconds": round(execution_time, 6),
                "error": None
            }
        except Exception as e:
            sys.stdout = sys.stdout if 'old_stdout' not in locals() else old_stdout
            return {
                "success": False,
                "execution_time_seconds": 0.0,
                "error": str(e)
            }

sandbox_runner = SandboxRunner()
