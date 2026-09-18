import json
import tarfile
import time
from pathlib import Path

ROOT = Path(r"G:/AI/E-zzio").resolve()
BACKUP_DIR = ROOT / "runtime" / "backups"

def backup_ezzio(destination_dir: str = None) -> dict:
    target_dir = Path(destination_dir) if destination_dir else BACKUP_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    archive_name = f"ezzio_backup_{timestamp}.tar.gz"
    archive_path = target_dir / archive_name

    items_to_backup = [
        ROOT / "runtime" / "test_tmp",
        ROOT / "core" / "constitution",
        ROOT / "_forensic" / "knowledge",
    ]

    backed_up_files = []
    with tarfile.open(archive_path, "w:gz") as tar:
        for item in items_to_backup:
            if item.exists():
                arcname = item.relative_to(ROOT)
                tar.add(item, arcname=str(arcname))
                backed_up_files.append(str(arcname))

    manifest = {
        "timestamp": timestamp,
        "archive": archive_name,
        "archive_path": str(archive_path),
        "size_bytes": archive_path.stat().st_size,
        "items": backed_up_files,
        "status": "SUCCESS"
    }

    manifest_path = target_dir / f"manifest_{timestamp}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest

def verify_backup(manifest_path: str) -> bool:
    m_path = Path(manifest_path)
    if not m_path.exists():
        return False
    data = json.loads(m_path.read_text(encoding="utf-8"))
    arc_path = Path(data["archive_path"])
    if not arc_path.exists():
        return False
    with tarfile.open(arc_path, "r:gz") as tar:
        members = tar.getmembers()
        return len(members) > 0

if __name__ == "__main__":
    res = backup_ezzio()
    print("Backup completed:", res["archive"], f"({res['size_bytes']} bytes)")
    verified = verify_backup(str(BACKUP_DIR / f"manifest_{res['timestamp']}.json"))
    print("Backup verified:", verified)
