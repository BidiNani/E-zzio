# Architecture d'E-ZZIO OS (v0.3.0-stable)

E-ZZIO repose sur une architecture modulaire en couches, privilégiant la souveraineté locale (TIER-1 CPU) avec un mécanisme de gouvernance et de persistance transactionnelle (WAL + FTS5).

\\mermaid
graph TD
    subgraph Interfaces ["1. INTERFACES"]
        API[FastAPI Server<br/>interfaces/api/server.py]
        Discord[Discord Bot Runner<br/>runtime/discord/bot_runner.py]
    end

    subgraph Core ["2. NOYAU COGNITIF (EzzioCore)"]
        CoreEngine[EzzioCore.think]
        Intent[IntentRouter]
        Guard[PromptGuard & QuotaManager]
    end

    subgraph Memory ["3. PERSISTANCE WAL & FTS5"]
        Gateway[UnifiedMemoryGateway]
        DB[(evidence.db<br/>SQLite WAL + FTS5)]
    end

    subgraph Providers ["4. MOTEURS D'INFÉRENCE"]
        Ollama[Ollama Local<br/>Qwen 3.5 100% CPU]
        Cloud[Gemini / Tavily / Jina]
    end

    API --> CoreEngine
    Discord --> CoreEngine
    CoreEngine --> Intent
    CoreEngine --> Guard
    CoreEngine --> Gateway
    Gateway --> DB
    CoreEngine --> Ollama
    CoreEngine --> Cloud
\