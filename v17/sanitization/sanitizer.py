import re
from typing import Any, Dict, List, Union

SENSITIVE_KEY_PATTERNS = [
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"api_?key", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"auth", re.IGNORECASE),
]

SENSITIVE_VALUE_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"[a-zA-Z0-9_-]{24,}\.[a-zA-Z0-9_-]{6,}\.[a-zA-Z0-9_-]{27,}"), # discord token pattern
    re.compile(r"AIza[0-9A-Za-z-_]{35}"), # google api key pattern
    re.compile(r"gsk_[a-zA-Z0-9]{20,}"), # groq pattern
    re.compile(r"tvly-[a-zA-Z0-9]{20,}"), # tavily pattern
]

def sanitize_data(data: Any) -> Any:
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if any(p.search(str(k)) for p in SENSITIVE_KEY_PATTERNS):
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = sanitize_data(v)
        return cleaned
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, str):
        val = data
        for p in SENSITIVE_VALUE_PATTERNS:
            val = p.sub("[REDACTED_SECRET]", val)
        return val
    return data
