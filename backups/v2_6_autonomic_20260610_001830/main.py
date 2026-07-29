import os
import asyncio
from core.dispatcher import ezzio_dispatcher
from core.memory import ezzio_memory
from core.actions import toolbox

INBOX_PATH = r"G:\AI\E-zzio\sensory\processed\inbox.txt"

os.environ["OLLAMA_NUM_GPU"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["GGML_CUDA"] = "0"

async def process_inbox():
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
                detailed = await ezzio_dispatcher.route_detailed_async(content, speed="auto")
                print(f"E-ZZIO [{detailed['organ_label']} / {detailed['model']} / {detailed['speed']}] > {detailed['response']}")

            with open(INBOX_PATH, "w", encoding="utf-8") as f:
                f.write("")

async def main_loop():
    print("--- E-ZZIO v2.5 : Adaptive Nervous System ---")
    while True:
        await process_inbox()
        await asyncio.sleep(1)

def main():
    asyncio.run(main_loop())

if __name__ == "__main__":
    main()
