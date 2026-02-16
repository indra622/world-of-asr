"""
Forced Alignment processor (stub)

Provides an interface to run post-ASR alignment to obtain word timings.
Initial target: Qwen forced alignment.
"""
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class QwenForcedAligner:
    def __init__(self):
        self.is_ready = False

    def load(self):
        # Load models/resources here in a real implementation
        self.is_ready = True

    def align(self, audio_path: str, transcription_result: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_ready:
            self.load()
        # Stub: return unchanged result
        logger.warning("QwenForcedAligner.align is a stub; returning original result")
        return transcription_result

    def unload(self):
        self.is_ready = False

