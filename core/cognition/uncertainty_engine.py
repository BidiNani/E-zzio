"""
E-ZZIO Core — Cognitive Operating Layer (ECOL)
Module: uncertainty_engine.py
Description: Mesure la confiance et cartographie les zones d'inconnu.
"""

import logging

logger = logging.getLogger(__name__)


class UncertaintyEngine:
    def __init__(self):
        logger.debug("Initialisation du composant ECOL : %s", self.__class__.__name__)
        pass
