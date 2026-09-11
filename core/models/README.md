# E-ZZIO Autonomous Model Fabric

## Providers
Supported:
- Gemini
- Groq
- OpenRouter
- LiteLLM

Ollama is intentionally excluded.

## Credential policy
Credentials are read from environment variables only.

Expected names:
- GEMINI_API_KEY, GEMINI_API_KEY_2, ...
- GROQ_API_KEY, GROQ_API_KEY_2, ...
- OPENROUTER_API_KEY, OPENROUTER_API_KEY_2, ...
- LITELLM_API_KEY

Gateway URL: `EZZIO_LITELLM_BASE_URL` (Default: `http://127.0.0.1:4000`)

## Security
Secrets are never printed, serialized, or written into logs/telemetry.

## Lifecycle
DISCOVERED -> CANDIDATE -> QUALIFYING -> QUALIFIED -> ACTIVE -> (SUPERSEDED / QUARANTINED / RETIRED)