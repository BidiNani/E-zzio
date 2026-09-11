import re
import json
from collections import Counter


def estimate_tokens(text):
    # Approximation robuste pour modèles locaux : 1 token ≈ 4 caractères en moyenne.
    text = str(text or "")
    return max(1, int(len(text) / 4))


def normalize_ws(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def strip_noise(text):
    text = str(text or "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def split_sentences(text):
    text = strip_noise(text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]


def keywords(text, limit=20):
    words = re.findall(r"[A-Za-zÀ-ÿ0-9_\-]{3,}", str(text).lower())
    stop = {
        "les",
        "des",
        "une",
        "dans",
        "pour",
        "avec",
        "que",
        "qui",
        "sur",
        "pas",
        "plus",
        "aux",
        "est",
        "sont",
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "you",
        "your",
        "http",
        "https",
    }
    words = [w for w in words if w not in stop]
    return [w for w, _ in Counter(words).most_common(limit)]


def score_sentence(sentence, keyset):
    s = sentence.lower()
    score = 0
    for k in keyset:
        if k in s:
            score += 1
    if any(ch.isdigit() for ch in sentence):
        score += 1
    if "http" in s or "api" in s or "error" in s or "warning" in s:
        score += 2
    return score


def compress_text(text, max_chars=4000, mode="extractive"):
    original = str(text or "")
    original_tokens = estimate_tokens(original)

    if len(original) <= max_chars:
        return {
            "compressed": original,
            "original_chars": len(original),
            "compressed_chars": len(original),
            "estimated_tokens_before": original_tokens,
            "estimated_tokens_after": estimate_tokens(original),
            "ratio": 1.0,
            "mode": "none",
        }

    clean = strip_noise(original)

    if mode == "hard":
        compressed = clean[:max_chars].rstrip()
    else:
        sents = split_sentences(clean)
        keys = set(keywords(clean, limit=30))
        ranked = sorted(sents, key=lambda s: score_sentence(s, keys), reverse=True)

        selected = []
        used = 0

        for sent in ranked:
            add = len(sent) + 2
            if used + add > max_chars:
                continue
            selected.append(sent)
            used += add

        if not selected:
            compressed = clean[:max_chars].rstrip()
        else:
            # On remet dans l'ordre d'origine pour garder le sens.
            ordered = [s for s in sents if s in selected]
            compressed = "\n".join(f"- {normalize_ws(s)}" for s in ordered)

    return {
        "compressed": compressed,
        "original_chars": len(original),
        "compressed_chars": len(compressed),
        "estimated_tokens_before": original_tokens,
        "estimated_tokens_after": estimate_tokens(compressed),
        "ratio": round(len(compressed) / max(1, len(original)), 4),
        "mode": mode,
        "keywords": keywords(original, limit=20),
    }


def compress_json(obj, max_chars=6000):
    raw = json.dumps(obj, ensure_ascii=False, indent=2)
    return compress_text(raw, max_chars=max_chars, mode="extractive")


def compact_api_result(result, max_chars=6000):
    if not isinstance(result, dict):
        return compress_text(str(result), max_chars=max_chars)

    compact = {
        "ok": result.get("ok"),
        "cached": result.get("cached"),
        "provider": result.get("provider"),
        "status_code": result.get("status_code"),
        "rate_headers": result.get("rate_headers", {}),
    }

    data = result.get("data")
    if data is not None:
        compact["compressed_data"] = compress_json(data, max_chars=max_chars)
    else:
        compact["compressed_text"] = compress_text(result.get("text", ""), max_chars=max_chars)

    return compact
