import unittest
import json
import dataclasses
from pathlib import Path
from runtime.core.microkernel import RuntimeBuilder
from runtime.tools.tool_schema import ToolRequest
from runtime.core.context import TokenSigner

class TestMicroKernel(unittest.TestCase):
    def setUp(self):
        self.builder = RuntimeBuilder().with_allowed_level(0)
        self.runtime = self.builder.build()
        self.manifest_path = self.builder.manifest_provider.path

    def tearDown(self):
        self.runtime.stop()

    def test_token_tampering_mutation(self):
        req = ToolRequest(name="filesystem.read", arguments={"path": "runtime/kernel.py"})
        auth, _, token = self.runtime.policy.authorize(req, "test_session")
        self.assertTrue(auth)
        
        # Le VRAI scénario d'attaque : l'attaquant garde la signature, mais modifie une contrainte métier
        tampered_token = dataclasses.replace(token, timeout_sec=999.0)
        
        is_valid = TokenSigner.verify(tampered_token, self.runtime.key_manager.get_key())
        self.assertFalse(is_valid, "La vérification HMAC doit bloquer la mutation post-signature.")

    def test_manifest_real_hash_mutation(self):
        h1 = self.runtime.policy.manifest.get_manifest_hash()
        
        original_data = self.manifest_path.read_text(encoding="utf-8")
        try:
            data = json.loads(original_data)
            # Mutation silencieuse du timeout
            data["tools"]["filesystem.read"]["timeout_sec"] = 8
            self.manifest_path.write_text(json.dumps(data), encoding="utf-8")
            
            h2 = self.runtime.policy.manifest.get_manifest_hash()
            self.assertNotEqual(h1, h2, "Le vrai SHA256 doit changer même si mtime n'est pas fiable.")
        finally:
            self.manifest_path.write_text(original_data, encoding="utf-8")

if __name__ == "__main__":
    unittest.main()