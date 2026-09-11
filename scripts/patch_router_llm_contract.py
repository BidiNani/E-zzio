from pathlib import Path

p = Path(r"G:\AI\E-zzio\runtime\model_router\router.py")
txt = p.read_text(encoding="utf-8")

if "from types import SimpleNamespace" not in txt:
    txt = txt.replace("from datetime import datetime", "from datetime import datetime\nfrom types import SimpleNamespace")

start = txt.find("    def generate(self, request=None, **kwargs) -> Dict[str, Any]:")
if start == -1:
    start = txt.find("    def generate(self, request=None, **kwargs):")
if start == -1:
    raise SystemExit("generate() introuvable")

end = txt.find('\n    raise ValueError(f"Provider {provider} non supporté")', start)
if end == -1:
    raise SystemExit("fin generate() introuvable")
end = txt.find("\n", end + 1)

new_block = """    def generate(self, request=None, **kwargs):
        if request is None:
            request = {}

        if hasattr(request, "model_dump"):
            request = request.model_dump()
        elif hasattr(request, "__dict__"):
            request = vars(request)
        elif not isinstance(request, dict):
            request = {}

        request.update(kwargs)

        prompt = request.get("prompt") or request.get("content")
        if not prompt:
            raise ValueError("Requête LLM invalide : prompt/content absent")

        task = request.get("task", "general")
        model_name = self.select_model(task)
        model_config = self.catalog.get(model_name, {})
        provider = model_config.get("provider", "ollama")
        options = model_config.get("options", {})

        if provider == "ollama":
            from .providers.ollama import OllamaProvider
            provider_instance = OllamaProvider()

            result = provider_instance.generate(
                prompt=prompt,
                model=model_name,
                **options
            )

            if isinstance(result, dict):
                content = result.get("response") or result.get("content") or ""
                latency_ms = result.get("latency_ms", 0)
            else:
                content = getattr(result, "content", "")
                latency_ms = getattr(result, "latency_ms", 0)

            return SimpleNamespace(
                content=content,
                model_used=model_name,
                provider_used=provider,
                latency_ms=latency_ms,
                fallback_applied=False
            )

        raise ValueError(f"Provider {provider} non supporté")
"""

txt = txt[:start] + new_block + txt[end:]
p.write_text(txt, encoding="utf-8")
print("[OK] router.py patché")
