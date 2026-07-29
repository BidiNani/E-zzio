import os
import time
from core.dispatcher import ezzio_dispatcher
from core.memory import ezzio_memory
from core.actions import toolbox

INBOX_PATH = r"G:\AI\E-zzio\sensory\processed\inbox.txt"

os.environ["OLLAMA_NUM_GPU"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["GGML_CUDA"] = "0"

def process_inbox():
    if os.path.exists(INBOX_PATH) and os.path.getsize(INBOX_PATH) > 0:
        with open(INBOX_PATH, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if content:
            print(f"\n[SENSORY] Détection : {content}")

            if content.startswith("ACTION:"):
                parts = content.split(":", 3)
                result = "Action invalide."

                if len(parts) >= 4 and parts[1] == "create_file":
                    result = toolbox.create_file(parts[2], parts[3])
                elif len(parts) >= 3 and parts[1] == "create_folder":
                    result = toolbox.create_folder(parts[2])

                print(f"E-ZZIO > {result}")
                ezzio_memory.save_interaction(content, result, "ActionAgent")
            else:
                detailed = ezzio_dispatcher.route_detailed(content)
                print(f"E-ZZIO [{detailed['organ_label']} / {detailed['model']}] > {detailed['response']}")

            with open(INBOX_PATH, "w", encoding="utf-8") as f:
                f.write("")

def main():
    print("--- E-ZZIO v2.2 PRO : MoE vif + mémoire + actions sécurisées ---")
    while True:
        process_inbox()
        time.sleep(1)

if __name__ == "__main__":
    main()
