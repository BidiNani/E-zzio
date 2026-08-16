import os
import pickle
import numpy as np

try:
    from huggingface_hub import hf_hub_download
    HAS_HF = True
except ImportError:
    HAS_HF = False

VOICES_ORIG = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\voices.bin"
VOICES_NEW = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\voices_extended.bin"

def integrate_french_voice():
    print("--- CHARGEMENT DU DICTIONNAIRE DE VOIX ORIGINAL ---")
    with open(VOICES_ORIG, "rb") as f:
        voices_dict = pickle.load(f)
    
    print(f"Voix actuellement présentes : {len(voices_dict)}")

    target_voice = "ff_siwis"
    
    if target_voice in voices_dict:
        print(f"[INFO] La voix '{target_voice}' est déjà présente dans le dictionnaire.")
        return

    fr_data = None
    
    # Tentative de récupération du profil vocal via le dépôt officiel Hugging Face
    if HAS_HF:
        try:
            print("[*] Téléchargement du profil vocal ff_siwis depuis hexgrad/Kokoro-82M...")
            local_pt = hf_hub_download(repo_id="hexgrad/Kokoro-82M", filename=f"voices/{target_voice}.pt")
            import torch
            tensor_obj = torch.load(local_pt, map_location="cpu")
            if isinstance(tensor_obj, torch.Tensor):
                fr_data = tensor_obj.numpy()
            else:
                fr_data = np.array(tensor_obj)
            print("[OK] Voix téléchargée et convertie avec succès.")
        except Exception as e:
            print(f"[!] Échec du téléchargement direct HF : {e}")

    if fr_data is None:
        print("[!] Impossible de récupérer automatiquement le tenseur brut.")
        print("[!] Veuillez placer un fichier tenseur .npy ou .pt valide pour 'ff_siwis' de dimension (511, 1, 256).")
        return

    # Validation stricte du contrat de dimensions ONNX
    if fr_data.shape != (511, 1, 256):
        raise ValueError(f"Erreur de dimension ! Attendu (511, 1, 256), reçu {fr_data.shape}")

    voices_dict[target_voice] = fr_data
    print(f"[OK] Voix '{target_voice}' validée (shape: {fr_data.shape}) et fusionnée.")

    with open(VOICES_NEW, "wb") as f:
        pickle.dump(voices_dict, f)
    print(f"[OK] Nouveau fichier généré : {VOICES_NEW}")

if __name__ == "__main__":
    integrate_french_voice()
