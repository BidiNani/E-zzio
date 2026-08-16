import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

class EzzioModelRouter:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "config.json"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.default_model = self.config.get('default_model', 'gemma4e4b:latest')
        self.catalog = self.config.get('catalog', {})
        self.routes = self.config.get('routes', {})
    
    def select_model(self, task: str, complexity: str = 'low') -> str:
        if task in self.routes:
            model_name = self.routes[task]
            if model_name in self.catalog:
                return model_name
        return self.default_model
    
    def generate(self, request=None, **kwargs) -> Dict[str, Any]:
        # Compatibilité API E-ZZIO
        if request is None:
            request = {}
        # Normalisation : support dict, Pydantic, objets
        if hasattr(request, "model_dump"):
            request = request.model_dump()
        elif hasattr(request, "__dict__"):
            request = vars(request)
        elif not isinstance(request, dict):
            request = {}

        request.update(kwargs)

        # Extraction du prompt
        prompt = request.get("prompt") or request.get("content")
        if not prompt:
            raise ValueError("Requête LLM invalide : prompt absent")

        task = request.get('task', 'general')
        model_name = self.select_model(task)
        model_config = self.catalog.get(model_name, {})
        provider = model_config.get('provider', 'ollama')
        options = model_config.get('options', {})
        
        if provider == 'ollama':
            from .providers.ollama import OllamaProvider
            provider_instance = OllamaProvider()
            
            response = provider_instance.generate(
                prompt=prompt,
                model=model_name,
                **options
            )
            
            return {
                'response': response.get('response', ''),
                'model_used': model_name,
                'provider_used': provider,
                'latency_ms': response.get('latency_ms', 0)
            }
        
        raise ValueError(f"Provider {provider} non supporté")
