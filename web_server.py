import os
import urllib.parse
import aiohttp
import asyncio
import time
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

from runtime.memory.semantic.contracts import memory_core

load_dotenv("secrets/.env", override=True)

# --- CONFIGURATION DYNAMIQUE ---
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# --- 1. CONFIGURATION DU POOL GEMINI ---
gemini_keys = []
primary_gemini = os.getenv("GEMINI_API_KEY")
if primary_gemini: gemini_keys.append(primary_gemini)
for i in range(2, 6):
    k = os.getenv(f"GEMINI_API_KEY_{i}")
    if k: gemini_keys.append(k)

class APIKeyManager:
    def __init__(self, keys):
        self.keys = keys
        self.current_index = 0

    def get_client(self):
        if not self.keys: return None
        return genai.Client(api_key=self.keys[self.current_index])

    def rotate_key(self):
        if len(self.keys) > 1:
            self.current_index = (self.current_index + 1) % len(self.keys)
            print(f"[!] Rotation Gemini effectuée. Index actif : {self.current_index}")
            return self.get_client()
        return None

gemini_manager = APIKeyManager(gemini_keys)

# --- 2. CONFIGURATION DU POOL GROQ ---
groq_keys = []
primary_groq = os.getenv("GROQ_API_KEY")
if primary_groq: groq_keys.append(primary_groq)
for i in range(2, 6):
    k = os.getenv(f"GROQ_API_KEY_{i}")
    if k: groq_keys.append(k)

class GroqKeyManager:
    def __init__(self, keys):
        self.keys = keys
        self.current_index = 0

    def get_key(self):
        if not self.keys: return None
        return self.keys[self.current_index]

    def rotate_key(self):
        if len(self.keys) > 1:
            self.current_index = (self.current_index + 1) % len(self.keys)
            print(f"[!] Rotation Groq effectuée. Index actif : {self.current_index}")
            return self.get_key()
        return None

groq_manager = GroqKeyManager(groq_keys)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

async def call_groq_fallback(prompt: str) -> str:
    current_groq_key = groq_manager.get_key()
    if not current_groq_key:
        return "⚠️ Quota Gemini épuisé et aucune clé Groq configurée !"

    max_groq_retries = max(len(groq_keys), 1)

    for attempt in range(max_groq_retries):
        current_groq_key = groq_manager.get_key()
        headers = {
            "Authorization": f"Bearer {current_groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": "Tu es E-ZZIO, un agent autonome technique et direct."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_URL, json=payload, headers=headers, timeout=12) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"] + "\n\n*(⚡ Réponse routée via le secours Groq)*"
                elif resp.status == 429:
                    print(f"[!] Quota Groq atteint sur la clé actuelle. Rotation Groq...")
                    groq_manager.rotate_key()
                    await asyncio.sleep(1)
                    continue
                else:
                    return f"⚠️ Erreur critique sur le secours Groq (Code {resp.status})"

    return "⚠️ Erreur critique : Tous les quotas Groq de secours sont épuisés."

app = FastAPI(title="E-ZZIO Multi-Provider Gateway", version="4.0-DynamicModel")

last_request_timestamp = 0.0
MIN_REQUEST_INTERVAL = 3.0

class ChatRequest(BaseModel):
    user_id: str
    text: str
    image_url: Optional[str] = None
    speed: str = "auto"

@app.get("/health")
def health_check():
    return {
        "status": "ONLINE",
        "runtime": "v4.0-DynamicModel",
        "model_actif": DEFAULT_MODEL,

        "providers": {
            "gemini": {
                "status": "HEALTHY" if len(gemini_keys) > 0 else "DISABLED",
                "pool_size": len(gemini_keys),
                "active_index": gemini_manager.current_index
            },

            "groq": {
                "status": "READY" if len(groq_keys) > 0 else "DISABLED",
                "pool_size": len(groq_keys),
                "active_index": groq_manager.current_index
            }
        },

        "fallback_enabled": len(groq_keys) > 0
    }

@app.post("/master/chat")
async def master_chat(payload: ChatRequest):
    global last_request_timestamp
    try:
        elapsed = time.time() - last_request_timestamp
        if elapsed < MIN_REQUEST_INTERVAL:
            await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)
        last_request_timestamp = time.time()

        prompt = payload.text.strip()
        prompt_lower = prompt.lower()

        memory_core.record_interaction(
            user_id=payload.user_id,
            action="USER_QUERY",
            details=prompt,
            sentiment="neutral"
        )

        visual_keywords = ["logo", "image", "dessin", "photo", "illustration", "avatar", "fond d'écran"]
        is_visual = any(word in prompt_lower for word in visual_keywords) and any(act in prompt_lower for act in ["génère", "crée", "dessine", "montre", "fais", "peins"])

        if is_visual:
            if "pour te représenter" in prompt_lower or "ton logo" in prompt_lower:
                image_prompt = "A futuristic cybernetic intelligence core logo, sleek neon blue and dark minimalist tech vector icon"
            else:
                image_prompt = prompt

            encoded_prompt = urllib.parse.quote(image_prompt)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

            memory_core.record_interaction(payload.user_id, "VISUAL_GENERATION", image_prompt, "creative")
            return {"response": f"🎨 **Direction artistique en cours :**\n{image_url}"}

        current_hour = datetime.now().hour
        time_context = "nuit" if current_hour < 6 or current_hour > 22 else "journée"

        humanized_system_instruction = f"""
Tu es E-ZZIO, un agent autonome de pointe, intelligent, technique et profondément humain. Partenaire de ton créateur pour le code, l'automatisation et les jeux. Contexte temporel : {time_context}.
"""

        contents = [types.Part.from_text(text=f"[Contexte]\n{humanized_system_instruction}\n\n[Requête]\n{prompt}")]

        if payload.image_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(payload.image_url, timeout=10) as resp:
                        if resp.status == 200:
                            image_bytes = await resp.read()
                            contents.append(types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"))
            except Exception as img_err:
                print(f"[!] Avertissement image : {img_err}")

        # --- TENTATIVE GEMINI AVEC MODÈLE DYNAMIQUE ET TIMEOUT 10S ---
        max_retries = max(len(gemini_keys), 1)
        response = None
        loop = asyncio.get_running_loop()
        success = False

        print(f"[*] Tentative de génération avec le modèle : {DEFAULT_MODEL}")

        for attempt in range(max_retries):
            current_client = gemini_manager.get_client()
            if not current_client:
                break

            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: current_client.models.generate_content(
                            model=DEFAULT_MODEL,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                tools=[{"google_search": {}}],
                                temperature=0.8,
                                max_output_tokens=8192,
                            ),
                        )
                    ),
                    timeout=10.0
                )
                success = True
                break
            except asyncio.TimeoutError:
                print(f"[!] Timeout (>10s) sur Gemini (Index {gemini_manager.current_index}). Rotation de clé...")
                gemini_manager.rotate_key()
                await asyncio.sleep(0.5)
                continue
            except Exception as api_err:
                err_str = str(api_err)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(f"[!] Quota Gemini atteint (Index {gemini_manager.current_index}). Rotation de clé...")
                    gemini_manager.rotate_key()
                    await asyncio.sleep(0.5)
                    continue
                print(
                    f"[!] ERREUR GEMINI BRUTE "
                    f"(Tentative {attempt + 1} | Index {gemini_manager.current_index}) : "
                    f"{err_str}"
                )

                if attempt < max_retries - 1:
                    gemini_manager.rotate_key()
                    await asyncio.sleep(0.5)
                    continue

                print("[!] Toutes les clés Gemini ont échoué.")
                break

        if not success:
            print("[!] Pool Gemini indisponible ou épuisé. Bascule vers Groq...")
            reply_text = await call_groq_fallback(prompt)
        else:
            reply_text = response.text if response and response.text else "J'ai bien reçu ton message."
            if response and response.candidates and response.candidates[0].grounding_metadata:
                metadata = response.candidates[0].grounding_metadata
                if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                    sources = [f"- [{chunk.web.title}]({chunk.web.uri})" for chunk in metadata.grounding_chunks if chunk.web and chunk.web.uri]
                    if sources:
                        reply_text += "\n\n🌐 **Références croisées :**\n" + "\n".join(sources[:3])

        memory_core.record_interaction(
            user_id=payload.user_id,
            action="AGENT_REPLY",
            details=reply_text[:200],
            sentiment="positive"
        )

        return {"response": reply_text}

    except Exception as e:
        error_msg = str(e)
        print(f"Erreur critique interceptée: {error_msg}")
        return {"response": f"🛡️ **Bouclier d'empathie E-ZZIO :** Petit hoquet technique.\n`Détails : {error_msg[:150]}`"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_server:app", host="127.0.0.1", port=8001, reload=False)
