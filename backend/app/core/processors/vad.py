"""
Voice Activity Detection (VAD) processor stub.
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class VADProcessor:
    def __init__(self):
        self.ready = False

    def load(self):
        self.ready = True

    def process(self, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        if not self.ready:
            self.load()
        logger.warning("VADProcessor.process is a stub; returning original result")
        return transcription_result

    def unload(self):
        self.ready = False

