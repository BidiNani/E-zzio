"""E-ZZIO — isolation CPU CCD1 (Ryzen 9 5900X / Windows).

Masque 0xFFF000 = threads 12-23 = coeurs physiques 6-11 (CCD1).
CCD0 sanctuarisé pour les jeux. Priorité ABOVE_NORMAL (0x8000).
Echecs silencieux mais journalisés (jamais bloquants).
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("ezzio.cpu_tuning")

CCD1_MASK = 0xFFF000
ABOVE_NORMAL = 0x8000
OLLAMA_NAMES = {"ollama.exe", "ollama", "ollama_llama_server.exe"}

if os.name != "nt":
    CCD1_MASK = 0  # affinité Windows uniquement


def _set_affinity_psutil(proc, mask: int) -> bool:
    try:
        proc.cpu_affinity(list(_mask_to_cpus(mask)))
        return True
    except Exception:
        return False


def _mask_to_cpus(mask: int):
    cpu = 0
    m = mask
    while m:
        if m & 1:
            yield cpu
        cpu += 1
        m >>= 1


def _set_affinity_ctypes(pid: int | None, mask: int) -> bool:
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetCurrentProcess() if pid is None else k.OpenProcess(0x0200 | 0x0400, False, pid)
        if not h:
            return False
        ok = bool(k.SetProcessAffinityMask(h, mask))
        if pid is not None:
            k.CloseHandle(h)
        return ok
    except Exception:
        return False


def _set_priority(pid: int | None) -> bool:
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetCurrentProcess() if pid is None else k.OpenProcess(0x0200 | 0x0400, False, pid)
        if not h:
            return False
        ok = bool(k.SetPriorityClass(h, ABOVE_NORMAL))
        if pid is not None:
            k.CloseHandle(h)
        return ok
    except Exception:
        return False


def pin_to_ccd1(pid: int | None = None) -> dict:
    """Epingle le processus courant au CCD1 + priorité haute."""
    res = {"affinity": False, "priority": False}
    if os.name == "nt" and CCD1_MASK:
        try:
            import psutil
            proc = psutil.Process(pid) if pid else psutil.Process()
            res["affinity"] = _set_affinity_psutil(proc, CCD1_MASK)
            try:
                from psutil import ABOVE_NORMAL_PRIORITY_CLASS
                proc.nice(ABOVE_NORMAL_PRIORITY_CLASS)
                res["priority"] = True
            except Exception:
                res["priority"] = _set_priority(pid)
        except Exception:
            res["affinity"] = _set_affinity_ctypes(pid, CCD1_MASK)
            res["priority"] = _set_priority(pid)
    else:
        logger.debug("[CPU-OPT] affinité ignorée (non-Windows).")
    return res


def pin_ollama_to_ccd1() -> dict:
    """Epingle tous les processus Ollama au CCD1 + priorité haute."""
    out: dict = {"pinned": [], "denied": []}
    try:
        import psutil
    except Exception:
        logger.warning("[CPU-OPT] psutil indisponible, repli ctypes.")
        return out
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            name = (proc.info.get("name") or "").lower()
        except Exception:
            continue
        if name in OLLAMA_NAMES:
            pid = proc.info["pid"]
            ok_a = _set_affinity_psutil(proc, CCD1_MASK)
            try:
                from psutil import ABOVE_NORMAL_PRIORITY_CLASS
                proc.nice(ABOVE_NORMAL_PRIORITY_CLASS)
                ok_p = True
            except Exception:
                ok_p = _set_priority(pid)
            (out["pinned"] if (ok_a or ok_p) else out["denied"]).append(pid)
    if out["denied"]:
        logger.warning("[CPU-OPT] Ollama inaccessible (PID %s) : shell élevé requis.", out["denied"])
    return out
