"""
Triton ASR adapter stub.
"""
from typing import Dict, Any, Optional
from app.core.models.base import ASRModelBase
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class TritonASRModel(ASRModelBase):
    def __init__(self, model_size: str, device: str, model_type: str = "triton_ctc"):
        super().__init__(model_size, device)
        self.model_type = model_type
        self.client = None

    def load_model(self) -> None:
        if not settings.enable_triton:
            raise RuntimeError("Triton disabled")
        logger.info("Triton ASR stub loaded (no real client)")
        self.is_loaded = True

    def transcribe(self, audio_path: str, language: Optional[str], params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load_model()
        logger.warning("TritonASRModel.transcribe is a stub; returning empty segments")
        return {"segments": []}

    def unload_model(self) -> None:
        self.client = None
        self.is_loaded = False
        logger.debug("Triton ASR stub unloaded")

