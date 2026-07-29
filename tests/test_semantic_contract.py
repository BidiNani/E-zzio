import pytest
import os
from pydantic import ValidationError
from runtime.memory.semantic.contracts import (
    MemoryInteraction,
    WorkingMemorySchema,
    SemanticMemoryManager
)

def test_memory_interaction_validation():
    """Vérifie que le contrat Pydantic valide et caste correctement les données."""
    interaction = MemoryInteraction(
        user_id="user_123",
        action="search",
        details="Recherche du fichier pipeline.py",
        sentiment="positive"
    )
    assert interaction.user_id == "user_123"
    assert interaction.sentiment == "positive"
    # Le timestamp doit être généré automatiquement
    assert len(interaction.timestamp) > 10

def test_working_memory_schema_defaults():
    """Vérifie l'initialisation du schéma global."""
    schema = WorkingMemorySchema()
    assert schema.version == "3.1-SemanticCore"
    assert isinstance(schema.interactions, list)
    assert len(schema.interactions) == 0

def test_semantic_memory_manager_lifecycle(monkeypatch, tmp_path):
    """Teste le cycle de vie du manager avec un stockage isolé."""
    # Redirection des chemins constants vers le répertoire temporaire de Pytest
    mock_mem_dir = tmp_path / "memory"
    mock_mem_file = mock_mem_dir / "working_memory.json"
    mock_log_file = tmp_path / "infrastructure" / "discord_actions.log"
    
    monkeypatch.setattr("runtime.memory.semantic.contracts.MEMORY_DIR", str(mock_mem_dir))
    monkeypatch.setattr("runtime.memory.semantic.contracts.MEMORY_FILE", str(mock_mem_file))
    monkeypatch.setattr("runtime.memory.semantic.contracts.LOG_FILE", str(mock_log_file))
    
    # 1. Initialisation (doit créer les dossiers et le fichier JSON vierge)
    manager = SemanticMemoryManager()
    assert mock_mem_file.exists()
    
    # 2. Enregistrement d'une interaction
    success = manager.record_interaction("u_456", "test_action", "Ceci est un test")
    assert success is True
    assert mock_log_file.exists()
    
    # 3. Vérification de la persistance
    data = manager._load_raw()
    assert len(data["interactions"]) == 1
    assert data["interactions"][0]["user_id"] == "u_456"
    assert data["interactions"][0]["action"] == "test_action"

def test_semantic_memory_sliding_window(monkeypatch, tmp_path):
    """Vérifie que la mémoire ne dépasse jamais la limite des 100 interactions."""
    mock_mem_file = tmp_path / "working_memory.json"
    mock_log_file = tmp_path / "discord_actions.log"
    monkeypatch.setattr("runtime.memory.semantic.contracts.MEMORY_DIR", str(tmp_path))
    monkeypatch.setattr("runtime.memory.semantic.contracts.MEMORY_FILE", str(mock_mem_file))
    monkeypatch.setattr("runtime.memory.semantic.contracts.LOG_FILE", str(mock_log_file))
    
    manager = SemanticMemoryManager()
    
    # On injecte 105 interactions
    for i in range(105):
        manager.record_interaction("u_flood", "spam", f"Message_{i}")
        
    # Le manager doit avoir purgé les 5 plus anciennes pour garder 100 éléments
    data = manager._load_raw()
    assert len(data["interactions"]) == 100
    assert data["interactions"][-1]["details"] == "Message_104"
    assert data["interactions"][0]["details"] == "Message_5"
