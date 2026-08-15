"""
E-ZZIO V7.33 — Static Analyzer
Vérifie la syntaxe, l'absence de structures interdites et la propreté du code candidat.
"""
import ast

class StaticAnalyzer:
    @staticmethod
    def analyze_code(content: str) -> dict:
        try:
            tree = ast.parse(content)
            # Vérifications basiques d'interdiction (ex: pas d'imports dangereux comme os.system ou subprocess non contrôlés)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == "system":
                        return {"passed": False, "error": "FORBIDDEN_SYSTEM_CALL_DETECTED"}
            return {"passed": True, "error": None}
        except SyntaxError as e:
            return {"passed": False, "error": f"SYNTAX_ERROR: {e}"}

static_analyzer = StaticAnalyzer()
