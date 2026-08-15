import json
from pathlib import Path

import pytest

from core.runtime import backend_supervisor


@pytest.fixture
def isolated_state(monkeypatch, tmp_path: Path):
    state_file = tmp_path / "backend_crash_state.json"
    monkeypatch.setattr(backend_supervisor, "STATE_FILE", state_file)
    return state_file


def test_load_crash_state_returns_empty_when_file_absent(isolated_state):
    assert backend_supervisor.load_crash_state() == []


def test_save_then_load_crash_state_roundtrip(isolated_state):
    crashes = [100.0, 200.0]

    backend_supervisor.save_crash_state(crashes, locked=False)

    assert isolated_state.exists()
    payload = json.loads(isolated_state.read_text(encoding="utf-8"))
    assert payload == {"crashes": crashes, "locked": False}
    assert backend_supervisor.load_crash_state() == crashes


def test_load_crash_state_tolerates_invalid_json(isolated_state):
    isolated_state.write_text("{not valid json", encoding="utf-8")

    assert backend_supervisor.load_crash_state() == []


def test_locked_state_triggers_exit(isolated_state):
    isolated_state.write_text(
        json.dumps({"crashes": [1.0] * 5, "locked": True}),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc_info:
        backend_supervisor.load_crash_state()

    assert exc_info.value.code == 1
