"""
E-ZZIO Core — ECOL Pipeline
Module: capability_selector.py
Description: Détermine si la tâche requiert un LLM, un script local ou une API cloud.
"""
import logging

logger = logging.getLogger(__name__)

class CapabilitySelector:
    def __init__(self):
        logger.debug("Initialisation du pipeline ECOL : %s", self.__class__.__name__)

    def process(self, payload: dict) -> dict:
        # Implémentation logique à relier à la Gateway
        return payload
