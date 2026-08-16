import psutil

def check():
    api_running = False
    bot_running = False
    
    for p in psutil.process_iter(['name', 'cmdline']):
        try:
            cmd = " ".join(p.info['cmdline'] or [])
            if "uvicorn" in cmd and "interfaces.api.server:app" in cmd:
                api_running = True
            if "bot_runner.py" in cmd:
                bot_running = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
            
    print("=== ÉTAT DES SERVICES E-ZZIO (DAEMON) ===")
    print(f"  - API FastAPI (Port 8001) : {'🟢 ACTIF' if api_running else '🔴 ARRÊTÉ'}")
    print(f"  - Bot Discord Runner      : {'🟢 ACTIF' if bot_running else '🔴 ARRÊTÉ'}")

if __name__ == "__main__":
    check()
