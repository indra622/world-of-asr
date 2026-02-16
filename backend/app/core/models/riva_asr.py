"""
NVIDIA Riva ASR adapter stub.
"""
from typing import Dict, Any, Optional
from app.core.models.base import ASRModelBase
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class RivaASRModel(ASRModelBase):
    def __init__(self, model_size: str, device: str):
        super().__init__(model_size, device)
        self.session = None

    def load_model(self) -> None:
        if not settings.enable_riva:
            raise RuntimeError("Riva disabled")
        logger.info("Riva ASR stub loaded")
        self.is_loaded = True

    def transcribe(self, audio_path: str, language: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load_model()
        logger.warning("RivaASRModel.transcribe is a stub; returning empty segments")
        return {"segments": []}

    def unload_model(self) -> None:
        self.session = None
        self.is_loaded = False
        logger.debug("Riva ASR stub unloaded")

