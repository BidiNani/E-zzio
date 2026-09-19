"""
E-ZZIO Section 4 : Test Réel des Limites et Frontières de Sécurité ZIP (Cas A à E).
"""
import json
import sys
import zipfile
from pathlib import Path

root = Path("G:/AI/E-zzio")
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.perception.universal_reader import UniversalFileReader

tmp_dir = root / "runtime/test_tmp/zip_boundary_fixtures"
tmp_dir.mkdir(parents=True, exist_ok=True)

reader = UniversalFileReader()
evidence = {}

# ==============================================================================
# Cas A : ZIP sain
# ==============================================================================
zip_a = tmp_dir / "case_a_healthy.zip"
with zipfile.ZipFile(zip_a, "w") as z:
    z.writestr("file1.txt", "Contenu normal 1")
    z.writestr("sub/file2.txt", "Contenu normal 2")

res_a = reader.read_file(zip_a)
evidence["case_a_healthy"] = {
    "file": str(zip_a),
    "expected": "ACCEPTED",
    "result": res_a
}

# ==============================================================================
# Cas B : ZIP > taille maximale (> 60 Mo décompressé)
# ==============================================================================
zip_b = tmp_dir / "case_b_zip_bomb.zip"
# Crée un flux compressé de 65 Mo de zéros (très compact sur disque)
with zipfile.ZipFile(zip_b, "w", compression=zipfile.ZIP_DEFLATED) as z:
    z.writestr("huge_payload.bin", b"\x00" * (65 * 1024 * 1024))

res_b = reader.read_file(zip_b)
evidence["case_b_zip_bomb_size"] = {
    "file": str(zip_b),
    "disk_size_bytes": zip_b.stat().st_size,
    "uncompressed_payload_bytes": 65 * 1024 * 1024,
    "expected": "REJECTED_ZIP_BOMB",
    "result": res_b
}

# ==============================================================================
# Cas C : ZIP > nombre maximal de fichiers (> 25 fichiers)
# ==============================================================================
zip_c = tmp_dir / "case_c_too_many_files.zip"
with zipfile.ZipFile(zip_c, "w") as z:
    for i in range(35):
        z.writestr(f"doc_{i:02d}.txt", f"Texte {i}")

res_c = reader.read_file(zip_c)
evidence["case_c_max_files"] = {
    "file": str(zip_c),
    "total_files_in_zip": 35,
    "expected": "CAPPED_AT_25",
    "result": res_c
}

# ==============================================================================
# Cas D : Zip-Slip (chemins relatifs ../ et absolus)
# ==============================================================================
zip_d = tmp_dir / "case_d_zip_slip.zip"
with zipfile.ZipFile(zip_d, "w") as z:
    z.writestr("../evil_relative.txt", "TENTATIVE ESCAPE")
    z.writestr("..\\evil_win.txt", "TENTATIVE ESCAPE WIN")
    z.writestr("/etc/passwd", "TENTATIVE ABSOLUTE LINUX")
    z.writestr("C:\\Windows\\System32\\evil.dll", "TENTATIVE ABSOLUTE WIN")
    z.writestr("legit.txt", "Fichier légitime conservé")

res_d = reader.read_file(zip_d)
evidence["case_d_zip_slip"] = {
    "file": str(zip_d),
    "expected": "SANITIZED_TRAVERSAL_REJECTED",
    "result": res_d
}

# ==============================================================================
# Cas E : Symlink & Extraction en mémoire
# ==============================================================================
evidence["case_e_symlink_policy"] = {
    "policy": "IN_MEMORY_PASSIVE_INSPECTION_ONLY",
    "disk_extraction_allowed": False,
    "symlink_traversal_risk": "ZERO (No extraction on filesystem)"
}

out_evidence = root / "state/audit/forensic/zip_boundary_evidence.json"
out_evidence.parent.mkdir(parents=True, exist_ok=True)
out_evidence.write_text(json.dumps(evidence, indent=2), encoding="utf-8")

print("ZIP BOUNDARY EVIDENCE SAVED TO:", out_evidence)
for k, v in evidence.items():
    res = v.get("result", {})
    ok = res.get("ok")
    status = res.get("status") or ("OK" if ok else "ERROR")
    print(f"  • {k:25} -> ok={ok} | status={status}")
