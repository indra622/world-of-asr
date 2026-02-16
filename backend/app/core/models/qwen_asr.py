"""
Qwen ASR adapter (stub)

Implements ASRModelBase interface. If using a hosted API, add HTTP client logic here.
"""
from typing import Dict, Any, Optional
from app.core.models.base import ASRModelBase
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class QwenASRModel(ASRModelBase):
    def __init__(self, model_size: str, device: str):
        super().__init__(model_size, device)
        self.session = None

    def load_model(self) -> None:
        if not settings.enable_qwen:
            raise RuntimeError("Qwen ASR disabled")
        logger.info("Qwen ASR enabled (stub)")
        self.is_loaded = True

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load_model()

        # Placeholder: no real API call here
        logger.warning("QwenASRModel.transcribe is a stub; returning empty result")
        return {"segments": []}

    def unload_model(self) -> None:
        self.session = None
        self.is_loaded = False
        logger.debug("Qwen ASR unloaded")

