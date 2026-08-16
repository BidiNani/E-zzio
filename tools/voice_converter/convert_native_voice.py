import os
import numpy as np
import torch
from huggingface_hub import hf_hub_download

orig_path = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\voices.bin"
cand_path = r"G:\AI\E-zzio\runtime\realtime\models\kokoro\voices_extended.bin"

print("[*] Étape 1 : Chargement de la baseline .npz...")
voices_dict = {}
with np.load(orig_path) as data:
    for key in data.files:
        voices_dict[key] = data[key]
print(f"[OK] {len(voices_dict)} voix baseline chargées.")

print("\n[*] Étape 2 : Téléchargement du fichier natif officiel hexgrad/Kokoro-82M (voices/ff_siwis.pt)...")
pt_file = hf_hub_download(
    repo_id="hexgrad/Kokoro-82M",
    filename="voices/ff_siwis.pt"
)

print(f"[*] Chargement du tenseur PyTorch depuis : {pt_file}")
tensor_obj = torch.load(pt_file, map_location="cpu")

if isinstance(tensor_obj, torch.Tensor):
    fr_data = tensor_obj.numpy()
else:
    fr_data = np.array(tensor_obj)

if fr_data.dtype != np.float32:
    fr_data = fr_data.astype(np.float32)

print(f"\n[*] Étape 3 : Validation rigoureuse du contrat tensoriel...")
print(f"    - Shape reçue : {fr_data.shape}")
print(f"    - Dtype reçu  : {fr_data.dtype}")

REQUIRED_SHAPE = (511, 1, 256)
if fr_data.shape == REQUIRED_SHAPE and fr_data.dtype == np.float32:
    voices_dict["ff_siwis"] = fr_data
    print(f"[PASS CERTIFIÉ] Le tenseur respecte exactement le contrat {REQUIRED_SHAPE}.")
else:
    raise ValueError(f"[FAIL CRITIQUE] Contrat non respecté ! Attendu {REQUIRED_SHAPE} float32, reçu {fr_data.shape} {fr_data.dtype}")

print(f"\n[*] Étape 4 : Génération de la sandbox candidate : {cand_path}")
np.savez(cand_path, **voices_dict)
print(f"[OK] Fichier généré avec succès. Poids : {os.path.getsize(cand_path) / 1024:.2f} Ko")
