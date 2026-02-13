"""
Origin Whisper 모델 래퍼

기존 woa/events.py::origin_whisper_process 함수를 클래스 기반으로 리팩토링
"""
from typing import Dict, Any, Optional
import gc
import torch
import whisper_timestamped as whisper
from app.core.models.base import ASRModelBase
import logging

logger = logging.getLogger(__name__)


class OriginWhisperModel(ASRModelBase):
    """
    원본 Whisper (whisper-timestamped) 모델 래퍼

    whisper-timestamped 라이브러리를 사용한 타임스탬프 지원 전사 모델
    기존 Gradio 앱의 origin_whisper_process 로직을 그대로 재사용
    """

    def load_model(self) -> None:
        """
        모델 로딩

        기존 코드: woa/events.py:46-48
        """
        try:
            logger.info(f"Loading Origin Whisper: {self.model_size} on {self.device}")

            # GPU 메모리 정리 (기존 woa/events.py:46-47)
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()

            # 모델 로드 (기존 woa/events.py:48)
            self.model = whisper.load_model(self.model_size, device=self.device)

            self.is_loaded = True
            logger.info("Origin Whisper model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Origin Whisper: {e}")
            raise

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        전사 수행

        기존 코드: woa/events.py:51-59

        Args:
            audio_path: 오디오 파일 경로
            language: 언어 힌트 (예: "ko", None이면 자동 감지)
            params: 전사 파라미터 딕셔너리

        Returns:
            전사 결과 딕셔너리 (whisper-timestamped 포맷)
            {
                "segments": [
                    {
                        "start": float,
                        "end": float,
                        "text": str,
                        "words": [...] (단어별 타임스탬프)
                    },
                    ...
                ]
            }
        """
        if not self.is_loaded:
            self.load_model()

        try:
            logger.info(f"Transcribing with Origin Whisper: {audio_path}")

            # 오디오 로드 (기존 woa/events.py:51)
            audio = whisper.load_audio(audio_path)

            # 전사 수행 (기존 woa/events.py:52-59)
            result = whisper.transcribe(
                self.model,
                audio,
                beam_size=params.get("beam_size", 5),
                language=language or None,
                vad='auditok',
                temperature=params.get("temperature", 0),
                condition_on_previous_text=params.get("condition_on_previous_text", False),
                initial_prompt=params.get("initial_prompt"),
                length_penalty=params.get("length_penalty", 0) or None,
                patience=params.get("patience", 0) or None,
                compression_ratio_threshold=params.get("compression_ratio_threshold", 2.4),
                logprob_threshold=params.get("logprob_threshold", -1),
                no_speech_threshold=params.get("no_speech_threshold", 0.6),
                remove_punctuation_from_words=params.get("remove_punctuation_from_words", False),
                remove_empty_words=params.get("remove_empty_words", False),
            )

            logger.info(f"Origin Whisper completed: {len(result['segments'])} segments")
            return result

        except Exception as e:
            logger.error(f"Origin Whisper failed for {audio_path}: {e}")
            raise

    def unload_model(self) -> None:
        """
        메모리 정리

        기존 코드: woa/events.py:62-64
        """
        if self.model is not None:
            logger.info("Unloading Origin Whisper model")
            del self.model
            self.model = None
            self.is_loaded = False

            # GPU 메모리 정리
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()

            logger.debug("Origin Whisper model unloaded, memory cleared")
