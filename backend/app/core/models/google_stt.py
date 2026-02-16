"""
Google Cloud Speech-to-Text adapter (stub)

Implements ASRModelBase interface. Requires google-cloud-speech (v2) if enabled.
This is a scaffolding that can be extended to real API calls.
"""
from typing import Dict, Any, Optional
from app.core.models.base import ASRModelBase
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class GoogleSTTModel(ASRModelBase):
    def __init__(self, model_size: str, device: str):
        super().__init__(model_size, device)
        self.client = None

    def load_model(self) -> None:
        if not settings.enable_google:
            raise RuntimeError("Google STT disabled")
        # Lazy import to avoid hard dependency
        try:
            from google.cloud import speech_v2  # type: ignore
        except Exception as e:
            raise ImportError("google-cloud-speech not installed") from e

        logger.info("Initializing Google STT client")
        # NOTE: Authentication is handled via service account or ADC.
        self.client = speech_v2.SpeechClient()
        self.is_loaded = True

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load_model()

        # Placeholder implementation: return empty structure
        # Extend to perform batch recognition with speech_v2 API.
        logger.warning("GoogleSTTModel.transcribe is a stub; returning empty result")
        return {"segments": []}

    def unload_model(self) -> None:
        self.client = None
        self.is_loaded = False
        logger.debug("Google STT client unloaded")

