"""
ASR 모델 추상 베이스 클래스
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ASRModelBase(ABC):
    """
    ASR 모델 추상 베이스 클래스

    모든 ASR 모델(Origin Whisper, FasterWhisper, FastConformer)이
    따라야 할 인터페이스를 정의합니다.
    """

    def __init__(self, model_size: str, device: str):
        """
        Args:
            model_size: 모델 크기 (tiny, base, small, medium, large, large-v3 등)
            device: 디바이스 (cpu, cuda)
        """
        self.model_size = model_size
        self.device = device
        self.model: Optional[Any] = None
        self.is_loaded = False

    @abstractmethod
    def load_model(self) -> None:
        """
        모델 로딩

        하위 클래스에서 구현해야 하는 메서드입니다.
        모델을 메모리에 로드하고 self.is_loaded를 True로 설정합니다.
        """
        pass

    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        전사 수행

        Args:
            audio_path: 오디오 파일 경로
            language: 언어 힌트 (예: "ko", None이면 자동 감지)
            params: 전사 파라미터 딕셔너리
                - beam_size: 빔 서치 크기
                - temperature: 샘플링 온도
                - patience: 조기 중단 patience
                - ... (모델별로 다를 수 있음)

        Returns:
            전사 결과 딕셔너리
            {
                "segments": [
                    {
                        "start": float,
                        "end": float,
                        "text": str,
                        "words": [...] (선택적)
                    },
                    ...
                ]
            }
        """
        pass

    @abstractmethod
    def unload_model(self) -> None:
        """
        메모리 정리

        모델을 메모리에서 해제하고 GPU 메모리를 정리합니다.
        self.is_loaded를 False로 설정합니다.
        """
        pass

    def __enter__(self):
        """
        컨텍스트 매니저 진입

        with 문을 사용할 때 자동으로 모델을 로드합니다.

        Example:
            with OriginWhisperModel("base", "cuda") as model:
                result = model.transcribe("audio.mp3", "ko", {...})
        """
        if not self.is_loaded:
            self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        컨텍스트 매니저 종료

        with 문이 끝나면 자동으로 메모리를 정리합니다.
        """
        self.unload_model()
