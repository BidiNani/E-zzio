import streamlit as st
import asyncio
import os
import sqlite3
from datetime import datetime

from core.memory.unified_gateway import UnifiedMemoryGateway
from runtime.core.ezzio_core import EzzioCore

st.set_page_config(page_title="E-ZZIO OS // JARVIS HUD", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ---- DESIGN CYBERPUNK / JARVIS ----
st.markdown(
    """
    <style>
    /* Fond global */
    .stApp {
        background: linear-gradient(135deg, #05070f 0%, #0a0f1f 100%);
        color: #00ffc8;
        font-family: "Courier New", Courier, monospace;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(10, 15, 30, 0.85);
        border-right: 1px solid #1f3a5a;
    }

    /* Titres */
    h1, h2, h3 {
        color: #00ffc8 !important;
        font-family: "Courier New", Courier, monospace;
        text-shadow: 0 0 8px rgba(0, 255, 200, 0.5);
    }

    /* Messages chat */
    .stChatMessage {
        background: rgba(6, 10, 20, 0.7);
        border: 1px solid #1f3a5a;
        border-radius: 8px;
        box-shadow: 0 0 10px rgba(0, 255, 200, 0.15);
    }

    /* Input chat */
    .stTextInput input {
        background: rgba(5, 8, 15, 0.9);
        color: #00ffc8;
        border: 1px solid #00ffc8;
        border-radius: 6px;
    }

    /* Boutons */
    .stButton > button {
        background: linear-gradient(90deg, #006f60, #00c2a8);
        color: #051018;
        border: none;
        border-radius: 6px;
        font-weight: bold;
        box-shadow: 0 0 8px rgba(0, 255, 200, 0.4);
    }

    /* Expander (télémétrie) */
    .streamlit-expanderHeader {
        color: #00ffc8 !important;
        font-weight: bold;
    }
    .streamlit-expanderContent {
        background: rgba(5, 8, 15, 0.6);
        border: 1px solid #1f3a5a;
        border-radius: 6px;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #05070f;
    }
    ::-webkit-scrollbar-thumb {
        background: #006f60;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #00c2a8;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ---- HEADER ----
col1, col2 = st.columns([3, 1])
with col1:
    st.title("⚡ E‑ZZIO OS // JARVIS HUD")
with col2:
    st.metric(label="Statut", value="EN LIGNE", delta=None)

st.markdown("---")

# ---- SIDEBAR ----
st.sidebar.markdown("### 🌐 SYSTÈMES & TIER‑1")
st.sidebar.text("Souveraineté : 100% CPU Local")
st.sidebar.text("Moteur : qwen3.5:9b")
st.sidebar.text("Sécurité : PromptGuard [ACTIVE]")
st.sidebar.markdown("---")
st.sidebar.text("Dernière màj : " + datetime.now().strftime("%H:%M:%S"))


# ---- CORE ----
@st.cache_resource
def load_core():
    mem = UnifiedMemoryGateway("runtime/evidence/evidence.db")
    return EzzioCore(memory_gateway=mem)


core = load_core()

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---- CHAT ----
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if user_input := st.chat_input("Entrez votre commande ou requête..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Traitement cognitif en cours..."):
            try:

                async def run_think():
                    return await core.think(user_id="enrik", message=user_input)

                res = asyncio.run(run_think())

                if isinstance(res, dict):
                    answer = res.get("response") or res.get("data", {}).get("text", str(res))
                else:
                    answer = str(res)
            except Exception as ex:
                answer = f"[-] Erreur d'exécution : {ex}"

        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})

# ---- TÉLÉMÉTRIE ----
with st.expander("🔍 Télémétrie et Traces SQLite (WAL)"):
    db_path = "runtime/evidence/evidence.db"
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("""
                SELECT timestamp, provider, mode, latency_ms, status
                FROM execution_traces
                ORDER BY id DESC
                LIMIT 10;
            """)
            rows = cur.fetchall()
            if rows:
                st.text("Dernières traces d'exécution :")
                for r in rows:
                    st.text(f"[{r[0]}] Provider: {r[1]} | Mode: {r[2]} | Latency: {r[3]}ms | Status: {r[4]}")
            else:
                st.text("Aucune trace pour l'instant.")
            conn.close()
        except Exception as e:
            st.text(f"Table non initialisée ou vide : {e}")
    else:
        st.text("Base de données evidence.db absente.")
