"""
FasterWhisper 모델 래퍼

기존 woa/events.py::whisper_process 함수를 클래스 기반으로 리팩토링
"""
from typing import Dict, Any, Optional
import gc
import torch
from faster_whisper import WhisperModel
from app.core.models.base import ASRModelBase
import logging

logger = logging.getLogger(__name__)


class FasterWhisperModel(ASRModelBase):
    """
    FasterWhisper 모델 래퍼

    faster-whisper 라이브러리를 사용한 고속 전사 모델
    기존 Gradio 앱의 whisper_process 로직을 그대로 재사용
    """

    def __init__(self, model_size: str, device: str, compute_type: str = "float16"):
        """
        Args:
            model_size: 모델 크기 (tiny, base, small, medium, large, large-v3)
            device: 디바이스 (cpu, cuda)
            compute_type: 연산 타입 (int8, float32, float16)
        """
        super().__init__(model_size, device)
        self.compute_type = compute_type if device == "cuda" else "int8"

    def load_model(self) -> None:
        """
        모델 로딩

        기존 코드: woa/events.py:132-136
        """
        try:
            logger.info(
                f"Loading FasterWhisper: {self.model_size} "
                f"on {self.device} (compute_type={self.compute_type})"
            )

            # GPU 메모리 정리 (기존 woa/events.py:132-133)
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()

            # 모델 로드 (기존 woa/events.py:136)
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )

            self.is_loaded = True
            logger.info("FasterWhisper model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load FasterWhisper: {e}")
            raise

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        전사 수행

        기존 코드: woa/events.py:116-141

        Args:
            audio_path: 오디오 파일 경로
            language: 언어 힌트 (예: "ko", None이면 자동 감지)
            params: 전사 파라미터 딕셔너리

        Returns:
            전사 결과 딕셔너리
            {
                "segments": [
                    {"start": float, "end": float, "text": str},
                    ...
                ]
            }
        """
        if not self.is_loaded:
            self.load_model()

        try:
            logger.info(f"Transcribing: {audio_path}")

            # ASR 옵션 구성 (기존 woa/events.py:116-128)
            asr_options = {
                "beam_size": params.get("beam_size", 5),
                "patience": None if params.get("patience", 0) == 0 else params["patience"],
                "length_penalty": None if params.get("length_penalty", 0) == 0 else params["length_penalty"],
                "temperatures": params.get("temperature", 0),
                "compression_ratio_threshold": params.get("compression_ratio_threshold", 2.4),
                "log_prob_threshold": params.get("logprob_threshold", -1),
                "no_speech_threshold": params.get("no_speech_threshold", 0.6),
                "condition_on_previous_text": params.get("condition_on_previous_text", False),
                "initial_prompt": params.get("initial_prompt") or None,
                "suppress_tokens": [-1],
                "suppress_numerals": True,
            }

            # 전사 수행 (기존 woa/events.py:139)
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                **asr_options
            )

            # 결과 포맷팅 (기존 woa/events.py:140)
            # format_output_largev3 함수는 woa/utils.py에서 가져옴
            from woa.utils import format_output_largev3
            result = format_output_largev3(segments)

            logger.info(f"Transcription completed: {len(result['segments'])} segments")
            return result

        except Exception as e:
            logger.error(f"Transcription failed for {audio_path}: {e}")
            raise

    def unload_model(self) -> None:
        """
        메모리 정리

        기존 코드: woa/events.py:143-145
        """
        if self.model is not None:
            logger.info("Unloading FasterWhisper model")
            del self.model
            self.model = None
            self.is_loaded = False

            # GPU 메모리 정리
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()

            logger.debug("FasterWhisper model unloaded, memory cleared")
