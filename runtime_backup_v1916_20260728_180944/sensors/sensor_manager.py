import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from runtime.sensors.system_sensor import SystemSensor
from runtime.sensors.filesystem_sensor import FilesystemSensor
from runtime.sensors.git_sensor import GitSensor
from runtime.sensors.health import SensorHealth

class SensorManager:
    def __init__(self, project_root=None, ttl_seconds=300):
        if project_root is None:
            # Résolution absolue garantie par rapport à l'emplacement de ce fichier
            project_root = Path(__file__).resolve().parents[2]
            
        self.project_root = Path(project_root).resolve()
        self.state_dir = self.project_root / "runtime" / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.world_state_file = self.state_dir / "world_state.json"
        
        self.ttl_seconds = ttl_seconds
        self.system_sensor = SystemSensor()
        self.filesystem_sensor = FilesystemSensor(self.project_root)
        self.git_sensor = GitSensor(self.project_root)
        self.health_monitor = SensorHealth(self.project_root)

    def collect(self, force: bool = False) -> dict:
        if not force and self.world_state_file.exists():
            try:
                cached_data = json.loads(self.world_state_file.read_text(encoding="utf-8"))
                updated_at_str = cached_data.get("updated_at")
                if updated_at_str:
                    updated_at = datetime.fromisoformat(updated_at_str)
                    if datetime.now() - updated_at < timedelta(seconds=self.ttl_seconds):
                        return cached_data
            except Exception:
                pass

        now = datetime.now()
        raw_payload = {
            "machine": self.system_sensor.scan(),
            "project": self.filesystem_sensor.scan(),
            "git": self.git_sensor.scan(),
            "health": self.health_monitor.check()
        }

        payload_bytes = json.dumps(raw_payload, sort_keys=True).encode("utf-8")
        snapshot_hash = hashlib.sha256(payload_bytes).hexdigest()[:16]
        snapshot_id = f"ws_{now.strftime('%Y%m%d_%H%M%S')}"

        world_data = {
            "world_snapshot_id": snapshot_id,
            "hash": snapshot_hash,
            "ttl_seconds": self.ttl_seconds,
            "updated_at": now.isoformat(),
            **raw_payload
        }

        self.world_state_file.write_text(json.dumps(world_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return world_data

    def get_world_state_prompt_block(self) -> str:
        data = self.collect()
        machine = data.get("machine", {})
        project = data.get("project", {})
        git = data.get("git", {})
        health = data.get("health", {})
        
        return f"""
[ÉTAT DU MONDE & PERCEPTION (Snapshot: {data.get('world_snapshot_id')} | Hash: {data.get('hash')})]
- Santé Capteurs : Système: {health.get('system_sensor')} | FS: {health.get('filesystem_sensor')} | Git: {health.get('git_sensor')}
- Machine : Python {machine.get('python')} | RAM libre: {machine.get('memory', {}).get('available')} | Ollama: {'En ligne' if machine.get('ollama') else 'Hors ligne'}
- Projet ({project.get('root')}): {project.get('files')} fichiers ({project.get('python_files')} Python, {project.get('powershell_files')} PowerShell) | Poids: {project.get('size_mb')} Mo | Modifié le: {project.get('last_change')}
- Git : Branche '{git.get('branch')}' | Statut: {git.get('status')} ({git.get('modified_files')} fichiers modifiés) | Dernier commit: "{git.get('last_commit')}"
"""