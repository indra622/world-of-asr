"""
모델 관리자 (싱글톤 패턴)

매 요청마다 모델을 재로드하지 않고 메모리에 캐싱하여 재사용
"""
from importlib import import_module
from typing import Dict, Optional, Type
import threading
import logging
from app.core.models.base import ASRModelBase
from app.core.models.faster_whisper import FasterWhisperModel
from app.core.models.whisper_original import OriginWhisperModel
from app.core.models.fast_conformer import FastConformerModel
from app.config import settings

logger = logging.getLogger(__name__)


def _load_optional_model(module_path: str, class_name: str) -> Optional[Type[ASRModelBase]]:
    try:
        module = import_module(module_path)
        model_class = getattr(module, class_name)
        return model_class
    except ImportError as exc:  # pragma: no cover
        logger.warning("Optional model unavailable: %s (%s)", class_name, exc)
        return None
    except Exception:  # pragma: no cover
        logger.exception("Failed to load optional model %s from %s", class_name, module_path)
        return None


GoogleSTTModel = _load_optional_model("app.core.models.google_stt", "GoogleSTTModel")
QwenASRModel = _load_optional_model("app.core.models.qwen_asr", "QwenASRModel")
NemoCTCModel = _load_optional_model("app.core.models.nemo_ctc", "NemoCTCModel")
NemoRNNTModel = _load_optional_model("app.core.models.nemo_rnnt", "NemoRNNTModel")
TritonASRModel = _load_optional_model("app.core.models.triton_asr", "TritonASRModel")
RivaASRModel = _load_optional_model("app.core.models.riva_asr", "RivaASRModel")


class ModelManager:
    """
    싱글톤 모델 관리자

    **주요 기능:**
    - 모델을 메모리에 캐싱하여 재사용 (성능 3-5배 향상)
    - 스레드 안전성 보장 (RLock 사용)
    - GPU 메모리 효율적 관리

    **사용 예시:**
    ```python
    from app.core.models.manager import model_manager

    # 모델 가져오기 (처음에는 로드, 이후에는 캐시에서)
    model = model_manager.get_model("faster_whisper", "large-v3", "cuda")

    # 전사 수행
    result = model.transcribe("/path/to/audio.mp3", "ko", {...})

    # 캐시 정리 (필요시)
    model_manager.clear_cache("faster_whisper")
    ```
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """
        싱글톤 패턴 구현

        애플리케이션 전체에서 단 하나의 ModelManager 인스턴스만 존재
        """
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    logger.info("ModelManager singleton instance created")
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._models: Dict[str, ASRModelBase] = {}
        self._model_lock = threading.RLock()
        self._initialized = True

    def get_model(
        self,
        model_type: str,
        model_size: str,
        device: str,
        compute_type: str = "float16"
    ) -> ASRModelBase:
        """
        모델 가져오기 (캐시에 없으면 새로 로드)

        Args:
            model_type: 모델 타입
                - "origin_whisper": whisper-timestamped
                - "faster_whisper": faster-whisper
                - "fast_conformer": NeMo FastConformer (Docker)
            model_size: 모델 크기
                - "tiny", "base", "small", "medium", "large", "large-v2", "large-v3"
            device: 디바이스
                - "cpu", "cuda"
            compute_type: 연산 타입 (FasterWhisper에서만 사용)
                - "int8", "float32", "float16"

        Returns:
            로드된 ASR 모델 인스턴스

        Raises:
            ValueError: 알 수 없는 모델 타입
        """
        # 캐시 키 생성
        if model_type == "faster_whisper":
            key = f"{model_type}_{model_size}_{device}_{compute_type}"
        else:
            key = f"{model_type}_{model_size}_{device}"

        with self._model_lock:
            if key not in self._models:
                logger.info(f"Loading new model: {key}")
                model = self._create_model(model_type, model_size, device, compute_type)
                model.load_model()
                self._models[key] = model
                logger.info(f"Model cached: {key} (total cached: {len(self._models)})")
            else:
                logger.info(f"Using cached model: {key}")

            return self._models[key]

    def _create_model(
        self,
        model_type: str,
        model_size: str,
        device: str,
        compute_type: str
    ) -> ASRModelBase:
        """
        모델 인스턴스 생성

        Args:
            model_type: 모델 타입
            model_size: 모델 크기
            device: 디바이스
            compute_type: 연산 타입

        Returns:
            ASR 모델 인스턴스

        Raises:
            ValueError: 알 수 없는 모델 타입
        """
        if model_type == "faster_whisper":
            return FasterWhisperModel(model_size, device, compute_type)
        elif model_type == "origin_whisper":
            return OriginWhisperModel(model_size, device)
        elif model_type == "fast_conformer":
            return FastConformerModel(model_size, device)
        elif model_type == "google_stt":
            if not settings.enable_google:
                raise ValueError("Google STT is disabled. Set enable_google=True")
            if GoogleSTTModel is None:
                raise ImportError("GoogleSTTModel not available (missing deps)")
            return GoogleSTTModel(model_size, device)
        elif model_type == "qwen_asr":
            if not settings.enable_qwen:
                raise ValueError("Qwen ASR is disabled. Set enable_qwen=True")
            if QwenASRModel is None:
                raise ImportError("QwenASRModel not available (missing deps)")
            return QwenASRModel(model_size, device)
        elif model_type == "nemo_ctc_offline":
            if not settings.enable_nemo:
                raise ValueError("NeMo disabled. Set enable_nemo=True")
            if NemoCTCModel is None:
                raise ImportError("NemoCTCModel not available")
            return NemoCTCModel(model_size, device)
        elif model_type == "nemo_rnnt_streaming":
            if not settings.enable_nemo:
                raise ValueError("NeMo disabled. Set enable_nemo=True")
            if NemoRNNTModel is None:
                raise ImportError("NemoRNNTModel not available")
            return NemoRNNTModel(model_size, device)
        elif model_type == "triton_ctc" or model_type == "triton_rnnt":
            if not settings.enable_triton:
                raise ValueError("Triton disabled. Set enable_triton=True")
            if TritonASRModel is None:
                raise ImportError("TritonASRModel not available")
            triton_model = TritonASRModel(model_size, device)
            triton_model.model_type = model_type
            return triton_model
        elif model_type == "nvidia_riva":
            if not settings.enable_riva:
                raise ValueError("Riva disabled. Set enable_riva=True")
            if RivaASRModel is None:
                raise ImportError("RivaASRModel not available")
            return RivaASRModel(model_size, device)
        else:
            raise ValueError(
                f"Unknown model type: {model_type}. "
                f"Supported types: origin_whisper, faster_whisper, fast_conformer, google_stt, qwen_asr, nemo_ctc_offline, nemo_rnnt_streaming, triton_ctc, triton_rnnt, nvidia_riva"
            )

    def clear_cache(self, model_type: Optional[str] = None):
        """
        모델 캐시 정리

        Args:
            model_type: 특정 타입만 정리 (None이면 전체 정리)
                - "origin_whisper": Origin Whisper 모델만 정리
                - "faster_whisper": FasterWhisper 모델만 정리
                - "fast_conformer": FastConformer 모델만 정리
                - None: 모든 모델 정리

        Example:
            # FasterWhisper 모델만 정리
            model_manager.clear_cache("faster_whisper")

            # 모든 모델 정리
            model_manager.clear_cache()
        """
        with self._model_lock:
            if model_type:
                # 특정 타입만 정리
                keys_to_remove = [
                    k for k in self._models.keys()
                    if k.startswith(model_type)
                ]

                for key in keys_to_remove:
                    logger.info(f"Unloading model: {key}")
                    self._models[key].unload_model()
                    del self._models[key]

                logger.info(
                    f"Cleared cache for model type: {model_type} "
                    f"({len(keys_to_remove)} models removed)"
                )
            else:
                # 전체 정리
                count = len(self._models)
                for model in self._models.values():
                    model.unload_model()
                self._models.clear()

                logger.info(f"Cleared all model cache ({count} models removed)")

    def get_cache_info(self) -> Dict[str, int]:
        """
        캐시 정보 조회

        Returns:
            모델 타입별 캐시된 모델 수
            {
                "origin_whisper": 1,
                "faster_whisper": 2,
                "fast_conformer": 0,
                "total": 3
            }
        """
        with self._model_lock:
            info = {
                "origin_whisper": 0,
                "faster_whisper": 0,
                "fast_conformer": 0,
                "total": len(self._models)
            }

            for key in self._models.keys():
                if key.startswith("origin_whisper"):
                    info["origin_whisper"] += 1
                elif key.startswith("faster_whisper"):
                    info["faster_whisper"] += 1
                elif key.startswith("fast_conformer"):
                    info["fast_conformer"] += 1

            return info


# 전역 싱글톤 인스턴스
# 애플리케이션 전체에서 이 인스턴스를 사용
model_manager = ModelManager()
