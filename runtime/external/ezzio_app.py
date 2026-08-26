import os
from flask import Flask, request, Response, stream_with_context
from openai import OpenAI

app = Flask(__name__)

# Client OpenRouter
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ.get("OPENROUTER_API_KEY", ""))

# LE BON MODÈLE (SANS LE :free)
MODEL_NAME = "meta-llama/llama-3.3-70b-instruct"


@app.route("/")
def index():
    return "E-zzio Core est en ligne !"


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")

    try:
        response_stream = client.chat.completions.create(
            model=MODEL_NAME, messages=[{"role": "user", "content": user_message}], stream=True
        )

        def generate():
            for chunk in response_stream:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

        return Response(stream_with_context(generate()), mimetype="text/plain")

    except Exception as e:
        return f"Erreur API : {str(e)}", 500


if __name__ == "__main__":
    print(f"🚀 [E-zzio] Serveur Flask initialisé (Modèle : {MODEL_NAME})")
    app.run(host="127.0.0.1", port=5000, debug=True)
