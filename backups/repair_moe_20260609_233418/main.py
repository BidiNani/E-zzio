import os
import time
from core.dispatcher import ezzio_dispatcher
from core.memory import ezzio_memory
from core.actions import toolbox

INBOX_PATH = r"G:\AI\E-zzio\sensory\processed\inbox.txt"

def process_inbox():
    if os.path.exists(INBOX_PATH) and os.path.getsize(INBOX_PATH) > 0:
        with open(INBOX_PATH, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if content:
            print(f"\n[SENSORY] Détection : {content}")
            
            # LOGIQUE : Si le message commence par 'ACTION:', on exécute
            if content.startswith("ACTION:"):
                # Format attendu : ACTION:create_file:nom.txt:contenu
                parts = content.split(":")
                action_type = parts[1]
                
                if action_type == "create_file":
                    res = toolbox.create_file(parts[2], parts[3])
                    print(f"E-zzio > {res}")
                
                ezzio_memory.save_interaction(content, res, "ActionAgent")
            
            else:
                # Sinon, on répond normalement
                response = ezzio_dispatcher.route(content)
                print(f"E-zzio > {response}")
                ezzio_memory.save_interaction(content, response, "Daemon")
            
            # Vide la boîte
            with open(INBOX_PATH, 'w', encoding='utf-8') as f: f.write("")

def main():
    print("--- E-ZZIO : MODE AGENT AUTONOME AVEC ACTION ACTIVÉ ---")
    while True:
        process_inbox()
        time.sleep(2)

if __name__ == '__main__':
    main()
