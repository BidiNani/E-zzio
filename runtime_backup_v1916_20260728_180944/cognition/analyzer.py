from dataclasses import dataclass, field
from typing import List

@dataclass
class TaskAnalysis:
    prompt: str
    estimated_tokens: int
    complexity_score: float
    keywords_detected: List[str] = field(default_factory=list)

class TaskAnalyzer:
    """Analyzes prompts to extract complexity and keywords for memory retrieval."""
    HEAVY_KEYWORDS = ["architecture", "refactor", "synthesis", "benchmark", "cloud", "security", "optimization"]
    STOPWORDS = {"les", "des", "une", "pour", "avec", "dans", "sur", "cette", "sont", "pourquoi", "comment", "fait", "faire", "tout", "plus", "cree", "crée"}

    @classmethod
    def analyze(cls, prompt: str) -> TaskAnalysis:
        words = prompt.lower().split()
        word_count = len(words)
        estimated_tokens = int(word_count * 1.3)

        detected_heavy = [kw for kw in cls.HEAVY_KEYWORDS if kw in prompt.lower()]
        score = min(1.0, (word_count / 150.0) * 0.4 + (len(detected_heavy) * 0.2))

        return TaskAnalysis(
            prompt=prompt,
            estimated_tokens=estimated_tokens,
            complexity_score=round(score, 2),
            keywords_detected=detected_heavy
        )

    @classmethod
    def extract_keywords(cls, prompt: str) -> List[str]:
        # Nettoyage robuste des apostrophes françaises (l', d', qu', etc.)
        normalized_prompt = prompt.lower()
        for prefix in ["l'", "d'", "qu'", "j'", "m'", "t'", "s'", "c'", "n'"]:
            normalized_prompt = normalized_prompt.replace(prefix, " ")

        raw_words = [w.strip("?,!.:;()\"'") for w in normalized_prompt.split()]
        valid_words = [w for w in raw_words if len(w) > 3 and w not in cls.STOPWORDS]
        return list(dict.fromkeys(valid_words))
