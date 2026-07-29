from runtime.memory.semantic.contracts import (
    SemanticMemoryManager
)


def test_memory_corruption_recovery(monkeypatch, tmp_path):

    memory_file = tmp_path / "broken.json"
    log_file = tmp_path / "log.txt"


    memory_file.write_text(
        "{ BROKEN JSON",
        encoding="utf-8"
    )


    monkeypatch.setattr(
        "runtime.memory.semantic.contracts.MEMORY_DIR",
        str(tmp_path)
    )

    monkeypatch.setattr(
        "runtime.memory.semantic.contracts.MEMORY_FILE",
        str(memory_file)
    )

    monkeypatch.setattr(
        "runtime.memory.semantic.contracts.LOG_FILE",
        str(log_file)
    )


    manager = SemanticMemoryManager()


    data = manager._load_raw()


    assert "interactions" in data
    assert isinstance(
        data["interactions"],
        list
    )
