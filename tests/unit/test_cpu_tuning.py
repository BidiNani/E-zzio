"""Tests pour core/system/cpu_tuning.py.

Ce module épingle les processus au CCD1 (Ryzen 9 5900X) et monte la priorité.
Il utilise psutil + ctypes Windows. Sur les appels système, on mocke psutil.

Notes :
- `CCD1_MASK` vaut 0xFFF000 sur Windows, 0 sur Linux/macOS.
- `_mask_to_cpus` est 100% pur (générateur) → test exhaustif.
- Les fonctions ctypes échouent silencieusement hors Windows → False.
"""
from __future__ import annotations

import os
import sys

import pytest

from core.system import cpu_tuning

# ============================================================
# 1. Smoke + constantes
# ============================================================

class TestSmoke:
    def test_module_imports(self):
        assert cpu_tuning is not None

    def test_ccd1_mask_value(self):
        """CCD1_MASK vaut 0xFFF000 sur Windows, 0 ailleurs."""
        if os.name == "nt":
            assert cpu_tuning.CCD1_MASK == 0xFFF000
        else:
            assert cpu_tuning.CCD1_MASK == 0

    def test_above_normal_constant(self):
        assert cpu_tuning.ABOVE_NORMAL == 0x8000

    def test_ollama_names(self):
        """OLLAMA_NAMES contient les 3 variantes attendues."""
        assert "ollama.exe" in cpu_tuning.OLLAMA_NAMES
        assert "ollama" in cpu_tuning.OLLAMA_NAMES
        assert "ollama_llama_server.exe" in cpu_tuning.OLLAMA_NAMES
        assert len(cpu_tuning.OLLAMA_NAMES) == 3


# ============================================================
# 2. _mask_to_cpus — générateur pur (LE test central)
# ============================================================

class TestMaskToCpus:
    def test_zero_mask(self):
        """Masque 0 -> aucun CPU."""
        assert list(cpu_tuning._mask_to_cpus(0)) == []

    def test_single_bit_0(self):
        """Masque 1 -> CPU 0."""
        assert list(cpu_tuning._mask_to_cpus(1)) == [0]

    def test_single_bit_12(self):
        """Masque 1<<12 -> CPU 12."""
        assert list(cpu_tuning._mask_to_cpus(1 << 12)) == [12]

    def test_ccd1_mask(self):
        """0xFFF000 -> CPUs 12 à 23 (12 CPUs)."""
        cpus = list(cpu_tuning._mask_to_cpus(0xFFF000))
        assert cpus == list(range(12, 24))
        assert len(cpus) == 12

    def test_contiguous_bits(self):
        """0b1111 (0xF) -> CPUs 0,1,2,3."""
        assert list(cpu_tuning._mask_to_cpus(0b1111)) == [0, 1, 2, 3]

    def test_alternating_bits(self):
        """0b1010101 -> CPUs 0,2,4,6."""
        assert list(cpu_tuning._mask_to_cpus(0b1010101)) == [0, 2, 4, 6]

    def test_full_24_bits(self):
        """0xFFFFFF -> CPUs 0 à 23 (24 CPUs)."""
        cpus = list(cpu_tuning._mask_to_cpus(0xFFFFFF))
        assert cpus == list(range(24))
        assert len(cpus) == 24

    def test_returns_generator(self):
        """_mask_to_cpus est un générateur (pas une liste)."""
        result = cpu_tuning._mask_to_cpus(0xFFF000)
        assert hasattr(result, "__iter__")
        assert not isinstance(result, list)


# ============================================================
# 3. _set_affinity_psutil — mock
# ============================================================

class TestSetAffinityPsutil:
    def test_success(self):
        """Si proc.cpu_affinity accepte, retourne True."""
        class FakeProc:
            def __init__(self):
                self.calls = []

            def cpu_affinity(self, cpus):
                self.calls.append(list(cpus))
                return True

        proc = FakeProc()
        result = cpu_tuning._set_affinity_psutil(proc, 0xFFF000)
        assert result is True
        assert proc.calls == [list(range(12, 24))]

    def test_failure_returns_false(self):
        """Si proc.cpu_affinity lève, retourne False."""
        class BadProc:
            def cpu_affinity(self, cpus):
                raise OSError("permission denied")

        result = cpu_tuning._set_affinity_psutil(BadProc(), 0xFFF000)
        assert result is False


# ============================================================
# 4. _set_affinity_ctypes — hors Windows retourne False
# ============================================================

class TestSetAffinityCtypes:
    def test_non_windows_returns_false(self):
        """Hors Windows, ctypes.windll n'existe pas -> False."""
        if os.name == "nt":
            pytest.skip("Test spécifique non-Windows")
        result = cpu_tuning._set_affinity_ctypes(None, 0xFFF000)
        assert result is False

    def test_never_raises(self):
        """Ne lève jamais d'exception, retourne toujours un bool."""
        result = cpu_tuning._set_affinity_ctypes(12345, 0xFFF000)
        assert isinstance(result, bool)


# ============================================================
# 5. _set_priority — hors Windows retourne False
# ============================================================

class TestSetPriority:
    def test_non_windows_returns_false(self):
        if os.name == "nt":
            pytest.skip("Test spécifique non-Windows")
        assert cpu_tuning._set_priority(None) is False

    def test_never_raises(self):
        result = cpu_tuning._set_priority(12345)
        assert isinstance(result, bool)


# ============================================================
# 6. pin_to_ccd1 — smoke + structure
# ============================================================

class TestPinToCcd1:
    def test_returns_dict_with_keys(self):
        """Retourne toujours un dict avec 'affinity' et 'priority'."""
        result = cpu_tuning.pin_to_ccd1()
        assert isinstance(result, dict)
        assert "affinity" in result
        assert "priority" in result
        assert isinstance(result["affinity"], bool)
        assert isinstance(result["priority"], bool)

    def test_non_windows_skips(self):
        """Hors Windows, aucun pin (retour vide)."""
        if os.name == "nt":
            pytest.skip("Test spécifique non-Windows")
        result = cpu_tuning.pin_to_ccd1()
        assert result == {"affinity": False, "priority": False}

    def test_with_fake_psutil_success(self, monkeypatch):
        """Mock psutil : les deux opérations réussissent."""
        class FakeProc:
            def cpu_affinity(self, cpus):
                return True
            def nice(self, value):
                return True

        class FakePsutil:
            ABOVE_NORMAL_PRIORITY_CLASS = 0x8000
            def Process(self, pid=None):
                return FakeProc()

        monkeypatch.setitem(sys.modules, "psutil", FakePsutil())
        # Forcer os.name en 'nt' pour ce test
        monkeypatch.setattr(os, "name", "nt")
        # Forcer CCD1_MASK non nul
        monkeypatch.setattr(cpu_tuning, "CCD1_MASK", 0xFFF000)

        result = cpu_tuning.pin_to_ccd1()
        assert result["affinity"] is True
        assert result["priority"] is True


# ============================================================
# 7. pin_ollama_to_ccd1 — smoke + structure
# ============================================================

class TestPinOllamaToCcd1:
    def test_returns_dict_with_lists(self):
        """Retourne un dict avec 'pinned' et 'denied' (listes)."""
        result = cpu_tuning.pin_ollama_to_ccd1()
        assert isinstance(result, dict)
        assert "pinned" in result
        assert "denied" in result
        assert isinstance(result["pinned"], list)
        assert isinstance(result["denied"], list)

    def test_no_psutil_returns_empty(self, monkeypatch):
        """Sans psutil, retourne {'pinned': [], 'denied': []}."""
        # Force l'échec de l'import psutil dans la fonction
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("simulated")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        result = cpu_tuning.pin_ollama_to_ccd1()
        assert result == {"pinned": [], "denied": []}

    def test_with_fake_ollama_processes(self, monkeypatch):
        """Avec 2 process Ollama, ils sont épinglés."""
        class FakeProc:
            def __init__(self, name, pid):
                self.info = {"name": name, "pid": pid}
            def cpu_affinity(self, cpus):
                return True
            def nice(self, value):
                return True

        class FakePsutil:
            ABOVE_NORMAL_PRIORITY_CLASS = 0x8000
            def __init__(self, procs):
                self._procs = procs
            def process_iter(self, attrs=None):
                return iter(self._procs)

        procs = [
            FakeProc("ollama.exe", 1001),
            FakeProc("notepad.exe", 1002),  # Pas Ollama
            FakeProc("ollama", 1003),
        ]
        fake_psutil = FakePsutil(procs)
        monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

        result = cpu_tuning.pin_ollama_to_ccd1()
        # Les 2 ollama doivent être dans pinned
        assert 1001 in result["pinned"]
        assert 1003 in result["pinned"]
        # Le notepad ne doit PAS être touché
        assert 1002 not in result["pinned"]
        assert 1002 not in result["denied"]
