from core.llm_engine import query_model
from talents.base_talent import BaseTalent

class Analyser(BaseTalent):
    def run(self, data):
        print(f"--- Analyse en cours via Qwen2.5-Coder ---")
        prompt = f"Analyse ce contenu de manière concise et utile : {data}"
        return query_model(prompt, model='qwen2.5-coder:7b')
