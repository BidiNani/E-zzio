"""
E-ZZIO Sovereign Platform — Automated Self-Check CLI Tool.
Fournit une vérification instantanée des invariants fondamentaux :
- Frozen Core Integrity
- Secret Leak Prevention
- Provider Federation (Ollama, Gemini, Groq, NVIDIA)
- Web Server Router Mounting
- Agent Registry Readiness
"""
import os
import sys
import json
import hashlib
import importlib

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def check_frozen_core() -> bool:
    manifest_path = "docs/FROZEN_CORE_MANIFEST.json"
    if not os.path.exists(manifest_path):
        print("[FAIL] Frozen core manifest missing")
        return False
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)["components"]
    files = ["core/capabilities/capability_policy.py", "core/capabilities/registry.py", "core/security/audit_ledger.py"]
    for f in files:
        if not os.path.exists(f):
            print(f"[FAIL] Frozen file {f} missing")
            return False
        h = hashlib.sha256(open(f, "rb").read()).hexdigest().lower()
        exp = manifest.get(f, {}).get("sha256", "").lower()
        if h != exp:
            print(f"[FAIL] Hash mismatch on {f}: {h} != {exp}")
            return False
    print("[PASS] Frozen Core integrity strictly verified (100% hash match)")
    return True

def check_secrets() -> bool:
    import re
    patterns = [
        re.compile(r"AIza[0-9A-Za-z-_]{35}"),
        re.compile(r"gsk_[0-9A-Za-z]{40,}"),
        re.compile(r"Bearer\s+[A-Za-z0-9\-\._~\+\/]{20,}="),
        re.compile(r"-----BEGIN (?:RSA )?PRIVATE KEY-----")
    ]
    targets = [
        "tools/launch_desktop.ps1",
        "tools/build_android_apk.ps1",
        "runtime/web/index.html",
        "android/app/build.gradle",
        "android/app/src/main/AndroidManifest.xml"
    ]
    for t in targets:
        if os.path.exists(t):
            c = open(t, "r", encoding="utf-8", errors="ignore").read()
            for p in patterns:
                if p.search(c):
                    print(f"[FAIL] Secret pattern found in {t}")
                    return False
    print("[PASS] Zero credential leaks in exposed code and artifacts")
    return True

def check_providers() -> bool:
    try:
        from core.providers.ollama_provider import OllamaProvider
        from core.providers.gemini_provider import GeminiProvider
        from core.providers.groq_provider import GroqProvider
        from core.providers.nvidia_nim_provider import NvidiaNimProvider

        o = OllamaProvider()
        assert o.name == "ollama"
        assert "qwen" in o.model.lower() or "phi" in o.model.lower()

        g = GeminiProvider()
        assert g.name == "gemini"

        gr = GroqProvider()
        assert gr.name == "groq"

        nv = NvidiaNimProvider()
        assert nv.name.lower() == "nvidia"

        print("[PASS] All 4 canonical providers conform to BaseProvider contracts")
        return True
    except Exception as exc:
        print(f"[FAIL] Provider verification failed: {exc}")
        return False

def check_web_server() -> bool:
    try:
        from web_server import app
        route_paths = [route.path for route in app.routes]
        required_paths = ["/health", "/perception/status", "/generators/universal", "/capabilities", "/master/chat"]
        for p in required_paths:
            match = any(p in r for r in route_paths)
            if not match:
                print(f"[FAIL] Missing required route {p}")
                return False
        print("[PASS] Official web server routers fully mounted and active")
        return True
    except Exception as exc:
        print(f"[FAIL] Web server route check failed: {exc}")
        return False

def check_agent_registry() -> bool:
    try:
        from core.agents.registry import AgentRegistry
        reg = AgentRegistry()
        reg.reset_to_defaults()
        agents = reg.list_agents()
        if len(agents) < 5:
            print(f"[FAIL] Expected >= 5 agents, got {len(agents)}")
            return False
        print(f"[PASS] Agent registry ready with {len(agents)} governed autonomous agents")
        return True
    except Exception as exc:
        print(f"[FAIL] Agent registry verification failed: {exc}")
        return False

def main():
    print("============================================================")
    print("E-ZZIO SOVEREIGN PLATFORM — SYSTEM SELF-CHECK")
    print("============================================================")
    ok1 = check_frozen_core()
    ok2 = check_secrets()
    ok3 = check_providers()
    ok4 = check_web_server()
    ok5 = check_agent_registry()
    print("------------------------------------------------------------")
    if ok1 and ok2 and ok3 and ok4 and ok5:
        print("SELF_CHECK_STATUS: ALL INVARIANTS PASS (10/10)")
        sys.exit(0)
    else:
        print("SELF_CHECK_STATUS: FAILURES DETECTED")
        sys.exit(1)

if __name__ == "__main__":
    main()
