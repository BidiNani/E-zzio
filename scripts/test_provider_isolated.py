"""
[DEPRECATED] Ce fichier importe un module runtime.* supprime (archive 2026-09-18).
A migrer ou supprimer. Ne pas utiliser en production.
"""

import sys

sys.path.insert(0, r"G:\AI\E-zzio")
from runtime.model_router.providers.ollama import OllamaProvider

p = OllamaProvider()
r = p.generate(prompt="ping", model="gemma4e4b:latest")
print("TYPE:", type(r))
print("RESULT:", r)
