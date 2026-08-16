import re

class AdaptiveStreamChunker:
    def __init__(self, max_tokens=500):
        # Marge de sécurité sous la limite 511
        self.max_tokens = max_tokens

    def chunk(self, text):
        # Split conservateur sur ponctuation forte et faible
        # On garde les délimiteurs pour ne pas perdre la structure
        segments = re.split(r'([.,!?;:\n])', text)
        
        chunks = []
        current_chunk = ""
        
        for i in range(0, len(segments), 2):
            part = segments[i]
            delim = segments[i+1] if i+1 < len(segments) else ""
            
            combined = (current_chunk + part + delim).strip()
            
            if len(combined) <= self.max_tokens:
                current_chunk = combined
            else:
                # Si le chunk actuel est plein, on yield et on repart
                if current_chunk:
                    chunks.append(current_chunk)
                
                # Si le nouveau morceau est trop long lui-même, on force un split
                if len(part + delim) > self.max_tokens:
                    # Split brutal par espace si vraiment trop long
                    sub_parts = part.split(' ')
                    temp = ""
                    for sp in sub_parts:
                        if len(temp) + len(sp) + 1 <= self.max_tokens:
                            temp += sp + " "
                        else:
                            chunks.append(temp.strip())
                            temp = sp + " "
                    current_chunk = temp.strip()
                else:
                    current_chunk = (part + delim).strip()
                    
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
