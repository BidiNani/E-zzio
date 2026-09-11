"""
Moteur avancé de compression de tokens et d'optimisation de contexte pour E-ZzIO.
Utilise tiktoken pour le calcul exact et des algorithmes de compression sémantique sans perte technique.
"""

import re
import logging
from typing import Any
import tiktoken

logger = logging.getLogger("EzzioTokenCompressor")


class TokenCompressor:
    def __init__(self, encoding_name: str = "cl100k_base") -> None:
        try:
            self.encoder = tiktoken.get_encoding(encoding_name)
        except Exception:
            self.encoder = None

    def count_tokens(self, text: str) -> int:
        """Compte précisément le nombre de tokens dans une chaîne."""
        if not text:
            return 0
        if self.encoder:
            try:
                return len(self.encoder.encode(text, disallowed_special=()))
            except Exception:
                pass
        # Heuristique de secours fiable (1 token ≈ 4 caractères)
        return max(1, len(text) // 4)

    def count_messages_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Compte les tokens totaux d'une liste de messages."""
        total = 0
        for m in messages:
            content = m.get("content", "") or ""
            role = m.get("role", "") or ""
            total += self.count_tokens(content) + self.count_tokens(role) + 4
        return total

    def compress_text(self, text: str) -> str:
        """
        Compresse le texte en supprimant les espaces superflus, les lignes vides multiples
        et les fioritures tout en préservant le sens technique.
        """
        if not text:
            return ""
            
        # 1. Remplacer les lignes vides multiples par une seule
        text = re.sub(r"\n{3,}", "\n\n", text)
        
        # 2. Supprimer les espaces de fin de ligne
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
        
        # 3. Réduire les séparateurs markdown trop longs (ex: -----------)
        text = re.sub(r"-{5,}", "---", text)
        text = re.sub(r"={5,}", "===", text)
        
        return text.strip()

    def compress_code(self, code: str) -> str:
        """Compresse du code sans altérer l'indentation ni la syntaxe."""
        if not code:
            return ""
        lines = code.splitlines()
        clean_lines = []
        consecutive_blank = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                consecutive_blank += 1
                if consecutive_blank <= 1:
                    clean_lines.append("")
            else:
                consecutive_blank = 0
                clean_lines.append(line.rstrip())
                
        return "\n".join(clean_lines)

    def prune_messages(
        self,
        messages: list[dict[str, Any]],
        max_tokens: int = 4000,
        keep_last_turns: int = 6
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        Élague et compresse l'historique des messages pour respecter le budget de tokens.
        Conserve toujours le message système initial et les N derniers tours.
        Produit un résumé des tours intermédiaires évincés.
        """
        if not messages:
            return [], None
            
        total_tokens = self.count_messages_tokens(messages)
        if total_tokens <= max_tokens and len(messages) <= (keep_last_turns * 2):
            return messages, None

        logger.info(
            "Élagage de contexte requis : %d tokens (Budget max: %d tokens, Total messages: %d)",
            total_tokens, max_tokens, len(messages)
        )

        # Isoler le message système s'il existe
        system_msg = None
        remaining_messages = list(messages)
        if remaining_messages and remaining_messages[0].get("role") == "system":
            system_msg = remaining_messages.pop(0)

        # Conserver les derniers tours
        tail_count = min(len(remaining_messages), keep_last_turns * 2)
        pruned_middle = remaining_messages[:-tail_count] if tail_count < len(remaining_messages) else []
        kept_tail = remaining_messages[-tail_count:] if tail_count > 0 else remaining_messages

        # Résumé synthétique des messages évincés
        summary_text = None
        if pruned_middle:
            topics = []
            for msg in pruned_middle:
                role = msg.get("role", "inconnu")
                content = (msg.get("content", "") or "")[:120].replace("\n", " ")
                topics.append(f"[{role}]: {content}...")
            summary_text = f"Résumé des {len(pruned_middle)} échanges précédents : " + " | ".join(topics[:4])

        # Reconstruction de la liste de messages finale
        final_msgs = []
        if system_msg:
            final_msgs.append(system_msg)
            
        if summary_text:
            final_msgs.append({
                "role": "system",
                "content": f"[Contexte mémoriel condensé] {summary_text}"
            })
            
        final_msgs.extend(kept_tail)
        return final_msgs, summary_text


_GLOBAL_COMPRESSOR: TokenCompressor | None = None


def get_token_compressor() -> TokenCompressor:
    global _GLOBAL_COMPRESSOR
    if _GLOBAL_COMPRESSOR is None:
        _GLOBAL_COMPRESSOR = TokenCompressor()
    return _GLOBAL_COMPRESSOR
