"""
E-ZZIO Core — Cognitive Operating Layer (ECOL)
Module: __init__.py
Description: Initialisation de la couche ECOL.
"""

import logging

logger = logging.getLogger(__name__)


class Init:
    def __init__(self):
        logger.debug("Initialisation du composant ECOL : %s", self.__class__.__name__)
        pass
