from typing import Tuple

TASK_PRIORITY_ORDER = [
    ("CRITICAL_OPERATION", ["supprime", "purge", "reset", "reformat", "shutdown", "éteins", "delete", "destroy"]),
    ("POWERSHELL", ["powershell", "ps1", "get-childitem", "set-executionpolicy", "cmdlet"]),
    ("PYTHON", ["python", "pytest", "fastapi", "sqlite3", "script python", "def "]),
    ("CODE", ["écris", "code", "fonction", "classe", "debug", "refactor", "programme"]),
    ("FORENSIC", ["forensic", "forensique", "baseline", "snapshot", "preuve", "sha256", "intégrité", "audit"]),
    ("STRUCTURED_JSON", ["json", "schéma", "pydantic", "export json", "format json"]),
    ("RESEARCH", ["recherche", "cherche sur le web", "documentation", "tavily", "trouve"]),
    ("LONG_CONTEXT", ["grand document", "longue conversation", "analyse complète du repo", "analyse globale"]),
    ("REASONING", ["pourquoi", "explique", "analyse", "compare", "démontre", "logique"]),
    ("FAST_REPLY", ["merci", "ok", "d'accord", "ping", "bonjour", "salut", "hello"]),
    ("CHAT", ["discute", "conversation", "qui es-tu"])
]

def classify_user_prompt(prompt: str) -> Tuple[str, str, float]:
    p_lower = prompt.lower()
    for task_type, keywords in TASK_PRIORITY_ORDER:
        if any(k in p_lower for k in keywords):
            complexity = "HIGH" if task_type in ["FORENSIC", "CODE", "POWERSHELL", "PYTHON", "CRITICAL_OPERATION"] else "LOW"
            return task_type, complexity, 0.95

    return "GENERAL", "MEDIUM", 0.70
