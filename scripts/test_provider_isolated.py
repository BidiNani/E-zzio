import sys
sys.path.insert(0, r"G:\AI\E-zzio")
from runtime.model_router.providers.ollama import OllamaProvider

p = OllamaProvider()
r = p.generate(prompt="ping", model="gemma4e4b:latest")
print("TYPE:", type(r))
print("RESULT:", r)
