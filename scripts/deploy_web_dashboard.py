from pathlib import Path

WEB_DIR = Path(r"G:\AI\E-zzio\runtime\web")
WEB_DIR.mkdir(parents=True, exist_ok=True)

html_content = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>E-ZZIO Control</title>
<script src="https://cdn.tailwindcss.com"></script>
<style>body{background:#0a0a0a; color:#e0e0e0;} .chat-box{height:70vh; overflow-y:auto;}</style></head>
<body class="p-4"><div class="max-w-3xl mx-auto">
<h1 class="text-xl font-bold mb-4 text-cyan-400">E-ZZIO Kernel Interface</h1>
<div id="chat" class="chat-box border border-neutral-800 p-4 mb-4 rounded bg-neutral-900"></div>
<div class="flex gap-2">
<input id="input" type="text" class="flex-1 bg-neutral-800 border border-neutral-700 p-2 rounded text-white" placeholder="Requête Kernel...">
<button onclick="send()" class="bg-cyan-900 px-4 py-2 rounded hover:bg-cyan-800">Envoyer</button>
</div></div>
<script>
async function send() {
    const input = document.getElementById('input');
    const chat = document.getElementById('chat');
    const msg = input.value;
    chat.innerHTML += `<div class="mb-2 text-right"><b>Vous:</b> ${msg}</div>`;
    input.value = '';
    const res = await fetch('/api/llm/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({prompt: msg, task: 'general'})
    });
    const data = await res.json();
    chat.innerHTML += `<div class="mb-2 text-left"><b>E-ZZIO:</b> ${data.content}</div>`;
    chat.scrollTop = chat.scrollHeight;
}
</script></body></html>"""

(WEB_DIR / "index.html").write_text(html_content, encoding="utf-8")
print("[OK] Dashboard UI déployé dans runtime/web/index.html.")
