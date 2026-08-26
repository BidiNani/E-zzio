import os
import ctypes
from ctypes import wintypes

# Définitions strictes pour Windows Job Object
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class WindowsProcessIsolator:
    """Encapsule un processus OS dans un Job Object pour garantir l'arrêt de l'arbre entier."""

    def __init__(self):
        self.job = None
        if os.name == "nt":
            try:
                self.job = ctypes.windll.kernel32.CreateJobObjectW(None, None)
                info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
                info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

                res = ctypes.windll.kernel32.SetInformationJobObject(self.job, 9, ctypes.pointer(info), ctypes.sizeof(info))
                if not res:
                    self.job = None
            except Exception:
                self.job = None

    def assign(self, process):
        if self.job and os.name == "nt":
            try:
                # Récupérer le handle du processus (process.handle n'est pas tjs dispo en pur python standard,
                # mais dans subprocess sous Windows, `_handle` contient le vrai handle OS).
                handle = getattr(process, "_handle", None)
                if handle:
                    ctypes.windll.kernel32.AssignProcessToJobObject(self.job, handle)
            except Exception:
                pass

    def close(self):
        if self.job and os.name == "nt":
            ctypes.windll.kernel32.CloseHandle(self.job)
            self.job = None
