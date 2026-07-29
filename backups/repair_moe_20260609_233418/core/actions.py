import os
import shutil

class ActionToolbox:
    def create_file(self, filename, content):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Fichier '{filename}' créé avec succès."

    def create_folder(self, foldername):
        if not os.path.exists(foldername):
            os.makedirs(foldername)
            return f"Dossier '{foldername}' créé."
        return f"Le dossier '{foldername}' existe déjà."

    def list_files(self, path="."):
        return str(os.listdir(path))

# Instance unique
toolbox = ActionToolbox()
