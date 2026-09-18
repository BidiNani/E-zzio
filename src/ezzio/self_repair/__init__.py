"""
Module d'auto-connaissance, d'inspection et d'auto-guérison d'E-ZzIO.
"""

from .auto_healer import AutoHealer
from .codebase_catalog import CodebaseCatalog, get_codebase_catalog

__all__ = ["CodebaseCatalog", "get_codebase_catalog", "AutoHealer"]
