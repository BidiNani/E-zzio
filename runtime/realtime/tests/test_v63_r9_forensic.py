import sys
import asyncio
import aiohttp
import json

sys.path.insert(0, r'G:\AI\E-zzio')

print("=" * 60)
print(" E-ZZIO V7 — FORENSIC R9: FORCE-FEED ANTI-THINKING")
print("=" * 60)

async def forensic_inspector():
    url = "http://localhost:11434/api/generate"
    # Forçage maximum pour neutraliser le 'thinking'
    payload = {
        "model": "qwen3:4b",
        "prompt": "Dis bonjour.",
        "stream": True,
        "think": False,
        "system": "Tu es un assistant vocal direct. Ne génère pas de réflexion interne. Réponds uniquement avec le contenu utile.",
        "options": {
            "num_predict": 512,
            "temperature": 0.1
        }
    }

    print("[DEBUG] Envoi requête avec système strict et think: False...")
    
    thinking_content = ""
    response_content = ""
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                async for line in resp.content:
                    if line:
                        data = json.loads(line.decode('utf-8'))
                        # Forensic : capture des deux champs
                        think = data.get("thinking", "")
                        resp_token = data.get("response") or data.get("message", {}).get("content", "")
                        
                        if think: thinking_content += think
                        if resp_token: response_content += resp_token
                        
                        if data.get("done"): break
        
        print("\n" + "="*40)
        print(f" 🧠 Total Thinking capté : {len(thinking_content)} chars")
        print(f" 💬 Total Response capté : {len(response_content)} chars")
        print("="*40)
        
        if len(response_content) == 0:
            print("❌ FAIL : Le modèle continue de monopoliser le budget avec 'thinking'.")
            sys.exit(1)
        else:
            print("✅ PASS : Le modèle a enfin produit une 'response' utile.")
            print(f"   Contenu : {response_content.strip()}")
            
    except Exception as e:
        print(f"❌ Exception : {e}")
        sys.exit(1)

asyncio.run(forensic_inspector())
