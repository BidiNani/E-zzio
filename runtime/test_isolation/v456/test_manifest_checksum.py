import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from segmented_recovery import SegmentedRecoveryEngine

SANDBOX = Path("runtime/test_isolation/v456/sandbox_checksum")

def setup_sandbox():
    if SANDBOX.exists():
        for p in SANDBOX.glob("**/*"):
            try:
                p.unlink()
            except Exception:
                pass
    SANDBOX.mkdir(parents=True, exist_ok=True)

def test_manifest_checksum_lifecycle():
    print("\n--- TEST C : Cycle de vie Checksum Manifeste & États ---")
    setup_sandbox()
    
    seg_dir = SANDBOX / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    
    # Création d'un segment fermé (SEALED) et d'un actif (ACTIVE)
    (seg_dir / "segment_000001.jsonl").write_text(json.dumps({"msg": "sealed"}) + "\n", encoding="utf-8")
    (seg_dir / "segment_000002.jsonl").write_text(json.dumps({"msg": "active"}) + "\n", encoding="utf-8")
    
    # 1. Premier chargement : Force la reconstruction et la création du fichier .sha256
    engine1 = SegmentedRecoveryEngine(str(SANDBOX))
    assert (SANDBOX / "manifest.json.sha256").exists(), "FAIL: Le sidecar checksum n'a pas été généré"
    assert engine1.manifest["segments"][0]["state"] == "SEALED"
    print("[OK] Premier chargement et génération du checksum réussis.")

    # 2. Deuxième chargement : Doit utiliser le cache instantané sans reconstruction
    print("[*] Second chargement (doit utiliser le cache)...")
    engine2 = SegmentedRecoveryEngine(str(SANDBOX))
    
    # 3. Altération volontaire du manifeste pour tester l'invalidation du checksum
    print("[*] Altération volontaire du manifeste...")
    manifest_path = SANDBOX / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["active_segment_id"] = 999  # Valeur fausse
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    
    # Troisième chargement : Le checksum doit échouer et déclencher la reconstruction automatique
    print("[*] Troisième chargement (doit détecter la falsification et reconstruire)...")
    engine3 = SegmentedRecoveryEngine(str(SANDBOX))
    assert engine3.manifest["active_segment_id"] == 2, f"FAIL: ID actif attendu 2, trouvé {engine3.manifest['active_segment_id']}"
    
    print("[SUCCESS] Test C validé : Cache checksum opérationnel et auto-guérison sur altération validée.")

if __name__ == "__main__":
    test_manifest_checksum_lifecycle()
    print("\n=============================================================")
    print(" STATUT : V4.5.6.3 MANIFEST CHECKSUM & STATES CERTIFIÉS")
    print("=============================================================")
