from pathlib import Path

micro_path = Path("runtime/core/microkernel.py")
code = micro_path.read_text(encoding="utf-8")

# S'assurer que le constructeur d'EzzioRuntime initialise bien self.signer et self.key_manager
if "self.signer" not in code:
    print("[*] Injection de self.signer dans EzzioRuntime.__init__...")
    # On cherche l'initialisation du microkernel
    target = "class EzzioRuntime:"
    init_target = "def __init__"
    if target in code:
        # Insertion des attributs de sécurité dans le constructeur
        code = code.replace(
            "self.event_bus = event_bus",
            "self.event_bus = event_bus\n        from runtime.security.guard import SecuritySigner, KeyManager\n        self.signer = SecuritySigner()\n        self.key_manager = KeyManager()"
        )
        micro_path.write_text(code, encoding="utf-8")
        print("[+] Attributs de sécurité injectés avec succès.")

print("[OK] Correction du microkernel appliquée.")
