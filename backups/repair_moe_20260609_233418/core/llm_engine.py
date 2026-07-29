import requests
import json

def get_persona():
    try:
        with open("G:/AI/E-zzio/registry/persona.txt", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "Tu es un assistant utile."

def query_model(prompt, model="llama3.1:8b"):
    persona = get_persona()
    full_prompt = f"{persona}\n\nUtilisateur : {prompt}\nE-zzio :"
    
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()["response"]
        else:
            return f"Erreur de connexion : {response.status_code}"
    except Exception as e:
        return f"Erreur lors de l'appel : {e}"
