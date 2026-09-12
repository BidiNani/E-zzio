"""
core/agent/capability_manager.py — Capability Profiles, Tool Discovery & Autonomous Preflight Manager for E-ZZIO Agents.
"""
from __future__ import annotations
import sys
import os
import logging
import importlib.util
import subprocess
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("ezzio.agent.capability_manager")

@dataclass
class CapabilityProfile:
    role: str
    tools: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)

# Registre des profils de capacités par rôle
CAPABILITY_PROFILES: Dict[str, CapabilityProfile] = {
    "CODING": CapabilityProfile(
        role="CODING",
        tools=["filesystem", "python", "git", "pytest", "database_connector", "input_extractor"],
        skills=["code_analysis", "implementation", "refactoring", "sql_analysis"],
        dependencies=["pytest", "httpx", "sqlite3"],
        permissions=["read_code", "write_code", "execute_cmd", "database.read", "input.read"]
    ),
    "FORENSIC": CapabilityProfile(
        role="FORENSIC",
        tools=["filesystem", "grep", "logs", "git", "sqlite", "input_extractor"],
        skills=["log_forensic", "audit", "traceability", "database_inspection"],
        dependencies=["sqlite3"],
        permissions=["read_code", "read_logs", "database.read", "database.query", "data.provenance", "input.read"]
    ),
    "REFACTOR": CapabilityProfile(
        role="REFACTOR",
        tools=["filesystem", "python"],
        skills=["refactoring", "clean_code"],
        dependencies=["ast"],
        permissions=["read_code", "write_code"]
    ),
    "RESEARCH": CapabilityProfile(
        role="RESEARCH",
        tools=["filesystem", "search", "http_api", "dataset_loader", "input_extractor"],
        skills=["information_retrieval", "api_data_access", "data_provenance", "web_extraction"],
        dependencies=["httpx", "sqlite3"],
        permissions=["read_code", "network_get", "api.public.read", "dataset.download", "database.read", "input.read", "web.read", "web.extract"]
    ),
    "DATA_ANALYSIS": CapabilityProfile(
        role="DATA_ANALYSIS",
        tools=["filesystem", "sqlite", "http_api", "dataset_loader", "input_extractor"],
        skills=["sql_analysis", "database_inspection", "data_retrieval", "data_provenance"],
        dependencies=["sqlite3", "httpx"],
        permissions=["database.read", "database.query", "api.public.read", "dataset.download", "data.provenance", "input.read"]
    ),
    "DOCUMENT": CapabilityProfile(
        role="DOCUMENT",
        tools=["filesystem", "pdf_parser", "input_extractor", "archive_tool"],
        skills=["document_analysis", "pdf_extraction", "archive_inspection"],
        dependencies=["httpx"],
        permissions=["input.read", "pdf.extract", "archive.inspect", "file.read"]
    ),
    "VISION": CapabilityProfile(
        role="VISION",
        tools=["filesystem", "image_inspector", "input_extractor"],
        skills=["visual_analysis", "image_metadata"],
        dependencies=["httpx"],
        permissions=["input.read", "image.read", "file.read"]
    ),
    "MEDIA": CapabilityProfile(
        role="MEDIA",
        tools=["filesystem", "audio", "stt", "input_extractor"],
        skills=["media_processing", "speech_processing"],
        dependencies=["wave", "struct"],
        permissions=["input.read", "audio.read", "video.read"]
    ),
    "TEST": CapabilityProfile(
        role="TEST",
        tools=["python", "pytest"],
        skills=["unit_testing", "regression"],
        dependencies=["pytest"],
        permissions=["read_code", "execute_cmd"]
    ),
    "VOICE": CapabilityProfile(
        role="VOICE",
        tools=["audio", "stt", "tts"],
        skills=["speech_processing"],
        dependencies=["wave", "struct"],
        permissions=["audio_io"]
    ),
    "FAST": CapabilityProfile(
        role="FAST",
        tools=["filesystem"],
        skills=["lightweight"],
        dependencies=[],
        permissions=["read_code"]
    ),
}


# Whitelist stricte des dépendances Python autorisées à l'installation autonome (sécurité anti-injection)
ALLOWED_DEPENDENCY_WHITELIST: set[str] = {
    dep for p in CAPABILITY_PROFILES.values() for dep in p.dependencies
}


class CapabilityManager:
    """Gestionnaire de capacités : preflight, vérification d'outils et installation autonome venv-local sécurisée."""

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or r"G:\AI\E-zzio"
        self.python_bin = sys.executable
        self._cache: Dict[str, bool] = {}

    def get_profile(self, role: str) -> CapabilityProfile:
        """Retourne le profil de capacités pour un rôle donné ou le profil FAST par défaut."""
        role_upper = (role or "").upper()
        return CAPABILITY_PROFILES.get(role_upper, CAPABILITY_PROFILES["FAST"])

    def check_external_tool(self, tool_name: str) -> bool:
        """Vérifie la présence d'un outil externe système (git, powershell, etc.) sans pip."""
        import shutil
        return shutil.which(tool_name) is not None or os.path.exists(tool_name)

    def check_dependency(self, package_name: str) -> bool:
        """Vérifie si un package Python est disponible dans le venv local."""
        if package_name in self._cache:
            return self._cache[package_name]

        # Built-in or installed package check
        try:
            spec = importlib.util.find_spec(package_name)
            is_available = spec is not None
        except Exception:
            is_available = False

        self._cache[package_name] = is_available
        return is_available

    def auto_install_dependency(self, package_name: str) -> bool:
        """Installe de manière autonome un package Python whitelisté dans le venv local du projet."""
        # 1. Contrôle de la Whitelist (sécurité anti-injection d'arguments)
        if package_name not in ALLOWED_DEPENDENCY_WHITELIST:
            logger.warning("[SECURITY-BLOCK] Refus d'installation autonome : '%s' hors whitelist.", package_name)
            return False

        # 2. Scope Venv local (interdiction d'installation système globale)
        logger.info("[CAPABILITY] Installation autonome venv-locale de '%s' (%s)...", package_name, self.python_bin)
        try:
            # Invocation directe par liste sans shell=True
            cmd = [self.python_bin, "-m", "pip", "install", package_name, "--isolated", "--quiet"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60, shell=False)

            if res.returncode == 0:
                # 3. Post-install Smoke Verification
                spec = importlib.util.find_spec(package_name)
                if spec is not None:
                    self._cache[package_name] = True
                    logger.info("[CAPABILITY] Package '%s' installé et vérifié avec succès.", package_name)
                    return True
                else:
                    logger.warning("[CAPABILITY] Package '%s' non importable post-install.", package_name)
                    return False
            else:
                logger.warning("[CAPABILITY] Échec pip install '%s' : %s", package_name, res.stderr)
                return False
        except Exception as exc:
            logger.error("[CAPABILITY] Erreur lors de l'installation de '%s' : %s", package_name, exc)
            return False

    def preflight_check(self, role: str, auto_install: bool = True) -> Dict[str, Any]:
        """Effectue le preflight des dépendances et outils requis pour un rôle agentique."""
        profile = self.get_profile(role)
        missing_deps = []
        installed_deps = []

        for dep in profile.dependencies:
            if not self.check_dependency(dep):
                if auto_install:
                    success = self.auto_install_dependency(dep)
                    if success:
                        installed_deps.append(dep)
                    else:
                        missing_deps.append(dep)
                else:
                    missing_deps.append(dep)

        is_ready = len(missing_deps) == 0

        result = {
            "role": profile.role,
            "ready": is_ready,
            "tools": profile.tools,
            "skills": profile.skills,
            "installed_deps": installed_deps,
            "missing_deps": missing_deps,
            "status": "READY" if is_ready else "BLOCKED"
        }
        return result


capability_manager = CapabilityManager()
