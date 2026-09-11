import pytest
import os
import time
from tools.fs_tools import observe_filesystem

def test_filesystem_observation_real_and_diff(tmp_path):
    obs_dir = tmp_path / "obs_target"
    obs_dir.mkdir()
    
    file_a = obs_dir / "alpha.txt"
    file_a.write_text("Alpha content", encoding="utf-8")
    
    # 1. Première observation
    snap1 = observe_filesystem(str(obs_dir))
    assert snap1["status"] == "SUCCESS"
    assert snap1["total_files"] == 1
    assert "alpha.txt" in snap1["files"]
    
    # 2. Ajout d'un nouveau fichier et modification de l'existant
    time.sleep(0.01)
    file_b = obs_dir / "beta.txt"
    file_b.write_text("Beta content", encoding="utf-8")
    file_a.write_text("Alpha content modified", encoding="utf-8")
    
    # Deuxième observation avec comparaison
    snap2 = observe_filesystem(str(obs_dir), previous_snapshot=snap1)
    assert snap2["status"] == "SUCCESS"
    assert snap2["total_files"] == 2
    assert "diff" in snap2
    assert "beta.txt" in snap2["diff"]["added"]
    assert "alpha.txt" in snap2["diff"]["modified"]
    
    # 3. Suppression d'un fichier
    file_a.unlink()
    snap3 = observe_filesystem(str(obs_dir), previous_snapshot=snap2)
    assert "alpha.txt" in snap3["diff"]["removed"]

def test_filesystem_observation_path_traversal_defense():
    snap = observe_filesystem("../../../etc/passwd")
    assert snap["status"] == "DENIED"

def test_filesystem_observation_nonexistent_directory():
    snap = observe_filesystem("non_existent_folder_xyz_999")
    assert snap["status"] == "NOT_FOUND"
