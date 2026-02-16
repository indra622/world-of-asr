# Phase 2: ASR 모델 통합 명세서

## 개요

Phase 1에서 구축한 FastAPI 백엔드 인프라에 기존 Gradio 기반 ASR 모델 로직을 통합합니다. 기존 `woa/events.py`의 함수형 코드를 클래스 기반으로 리팩토링하고, 모델 캐싱을 통해 성능을 개선합니다.

**예상 소요 시간**: 2-3주

## 목표

- ✅ 기존 ASR 모델 로직을 재사용하면서 코드 품질 개선
- ✅ 모델 싱글톤 패턴으로 메모리 효율성 확보
- ✅ 타입 안전성 확보 (타입 힌팅 추가)
- ✅ 테스트 가능한 코드 구조
- ✅ GPU 메모리 누수 방지

## 작업 목록

### 1. ASR 모델 추상 베이스 클래스 작성

**파일**: `backend/app/core/models/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ASRModelBase(ABC):
    """ASR 모델 추상 베이스 클래스"""

    def __init__(self, model_size: str, device: str):
        self.model_size = model_size
        self.device = device
        self.model: Optional[Any] = None
        self.is_loaded = False

    @abstractmethod
    def load_model(self) -> None:
        """모델 로딩 (하위 클래스에서 구현)"""
        pass

    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """전사 수행 (하위 클래스에서 구현)"""
        pass

    @abstractmethod
    def unload_model(self) -> None:
        """메모리 정리 (하위 클래스에서 구현)"""
        pass

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        if not self.is_loaded:
            self.load_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.unload_model()
```

**주요 기능:**
- 모든 ASR 모델이 따라야 할 인터페이스 정의
- Context Manager 지원 (`with` 문 사용 가능)
- 로딩 상태 추적
- 로깅 통합

---

### 2. FasterWhisper 모델 클래스 구현

**파일**: `backend/app/core/models/faster_whisper.py`

**기존 코드 위치**: `woa/events.py:83-163` (whisper_process 함수)

**리팩토링 방향:**
1. 함수 → 클래스 메서드
2. 전역 변수 제거
3. 타입 힌팅 추가
4. 에러 핸들링 강화

```python
from typing import Dict, Any, Optional
import gc
import torch
from faster_whisper import WhisperModel
from app.core.models.base import ASRModelBase
from app.core.processors.formatters import format_output_largev3
import logging

logger = logging.getLogger(__name__)

class FasterWhisperModel(ASRModelBase):
    """FasterWhisper 모델 래퍼"""

    def load_model(self) -> None:
        """모델 로딩"""
        try:
            logger.info(f"Loading FasterWhisper: {self.model_size} on {self.device}")

            # GPU 메모리 정리
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()

            # Compute type 결정
            compute_type = "float16" if self.device == "cuda" else "int8"

            # 모델 로드 (기존 whisper_process의 로직 그대로)
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=compute_type
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

        Args:
            audio_path: 오디오 파일 경로
            language: 언어 힌트 (예: "ko")
            params: 전사 파라미터 딕셔너리

        Returns:
            전사 결과 딕셔너리 (segments 포함)
        """
        if not self.is_loaded:
            self.load_model()

        try:
            logger.info(f"Transcribing: {audio_path}")

            # ASR 옵션 구성 (기존 woa/events.py:116-128과 동일)
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

            # 결과 포맷팅 (기존 woa/utils.py 재사용)
            result = format_output_largev3(segments)

            logger.info(f"Transcription completed: {len(result['segments'])} segments")
            return result

        except Exception as e:
            logger.error(f"Transcription failed for {audio_path}: {e}")
            raise

    def unload_model(self) -> None:
        """메모리 정리"""
        if self.model is not None:
            logger.info("Unloading FasterWhisper model")
            del self.model
            self.model = None
            self.is_loaded = False

            # GPU 메모리 정리
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()
```

**재사용 코드:**
- `woa/utils.py::format_output_largev3()` - 그대로 import
- 전사 로직은 기존 `whisper_process` 함수와 동일

---

### 3. Origin Whisper 모델 클래스 구현

**파일**: `backend/app/core/models/whisper_original.py`

**기존 코드 위치**: `woa/events.py:16-81` (origin_whisper_process 함수)

```python
from typing import Dict, Any, Optional
import gc
import torch
import whisper_timestamped as whisper
from app.core.models.base import ASRModelBase
import logging

logger = logging.getLogger(__name__)

class OriginWhisperModel(ASRModelBase):
    """원본 Whisper (whisper-timestamped) 모델 래퍼"""

    def load_model(self) -> None:
        """모델 로딩"""
        try:
            logger.info(f"Loading Origin Whisper: {self.model_size} on {self.device}")

            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()

            # 기존 woa/events.py:48과 동일
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
        """전사 수행"""
        if not self.is_loaded:
            self.load_model()

        try:
            logger.info(f"Transcribing with Origin Whisper: {audio_path}")

            # 오디오 로드 (기존 woa/events.py:51)
            audio = whisper.load_audio(audio_path)

            # 전사 (기존 woa/events.py:52-59과 동일)
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
        """메모리 정리"""
        if self.model is not None:
            logger.info("Unloading Origin Whisper model")
            del self.model
            self.model = None
            self.is_loaded = False
            gc.collect()
            if self.device == "cuda":
                torch.cuda.empty_cache()
```

---

### 4. FastConformer 모델 클래스 구현

**파일**: `backend/app/core/models/fast_conformer.py`

**기존 코드 위치**: `woa/events.py:165-256` (fastconformer_process 함수)

**⚠️ 보안 주의사항**: 기존 코드는 `ast.literal_eval()`을 사용하여 Docker 출력을 파싱합니다. 보안을 위해 JSON 포맷 사용을 권장하지만, Docker 컨테이너가 신뢰할 수 있는 환경이므로 기존 방식을 유지합니다.

```python
from typing import Dict, Any, Optional
import os
import json
import docker
from app.core.models.base import ASRModelBase
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class FastConformerModel(ASRModelBase):
    """FastConformer (NeMo) 모델 래퍼 - Docker 기반"""

    def __init__(self, model_size: str, device: str):
        super().__init__(model_size, device)
        self.docker_client = None
        self.container = None

    def load_model(self) -> None:
        """Docker 컨테이너 연결"""
        try:
            logger.info("Connecting to FastConformer Docker container")

            # 환경 변수 확인 (기존 woa/events.py:220-221)
            container_id = settings.container_id
            if not container_id:
                raise ValueError("CONTAINER_ID environment variable not set")

            # Docker 클라이언트 생성 (기존 woa/events.py:223-225)
            self.docker_client = docker.from_env()
            self.container = self.docker_client.containers.get(container_id)

            self.is_loaded = True
            logger.info(f"Connected to Docker container: {container_id}")

        except Exception as e:
            logger.error(f"Failed to connect to FastConformer container: {e}")
            raise

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """전사 수행 - Docker exec를 통해 NeMo 실행"""
        if not self.is_loaded:
            self.load_model()

        try:
            logger.info(f"Transcribing with FastConformer: {audio_path}")

            # Docker exec 실행 (기존 woa/events.py:234)
            result = self.container.exec_run(
                f"python run_nemo.py {audio_path}",
                stderr=False
            )

            # 결과 파싱
            # 참고: Docker 컨테이너가 신뢰할 수 있는 환경이므로 기존 방식 유지
            # 향후 개선: docker/run_nemo.py를 JSON 출력으로 수정 권장
            output = result.output.decode("utf-8")

            # JSON으로 파싱 시도
            try:
                parsed_result = json.loads(output)
            except json.JSONDecodeError:
                # 기존 방식 (ast.literal_eval) - 보안상 권장하지 않음
                import ast
                logger.warning("Using ast.literal_eval for parsing - consider migrating to JSON")
                parsed_result = ast.literal_eval(output)

            # 포맷 변환 (기존 woa/events.py:236)
            # parsed_result는 [result, filename] 형태
            transcription_result = parsed_result[0][0]

            logger.info(f"FastConformer completed")
            return transcription_result

        except Exception as e:
            logger.error(f"FastConformer failed for {audio_path}: {e}")
            raise

    def unload_model(self) -> None:
        """Docker 연결 종료"""
        if self.docker_client is not None:
            logger.info("Closing Docker client connection")
            self.docker_client.close()
            self.docker_client = None
            self.container = None
            self.is_loaded = False
```

**주의사항:**
- `docker/run_nemo.py`는 그대로 재사용
- Docker 컨테이너가 사전에 실행되어 있어야 함
- 향후 개선: `docker/run_nemo.py`를 JSON 출력으로 수정하면 보안성 향상

---

### 5. 모델 매니저 (싱글톤) 구현

**파일**: `backend/app/core/models/manager.py`

**목적**: 모델 캐싱으로 매 요청마다 모델을 재로드하지 않음

```python
from typing import Dict, Optional
import threading
from app.core.models.base import ASRModelBase
from app.core.models.faster_whisper import FasterWhisperModel
from app.core.models.whisper_original import OriginWhisperModel
from app.core.models.fast_conformer import FastConformerModel
import logging

logger = logging.getLogger(__name__)

class ModelManager:
    """
    싱글톤 모델 관리자

    - 모델을 메모리에 캐싱하여 재사용
    - 스레드 안전성 보장
    - GPU 메모리 효율적 관리
    """

    _instance: Optional['ModelManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._models: Dict[str, ASRModelBase] = {}
                    cls._instance._model_lock = threading.RLock()
        return cls._instance

    def get_model(
        self,
        model_type: str,
        model_size: str,
        device: str
    ) -> ASRModelBase:
        """
        모델 가져오기 (캐시에 없으면 새로 로드)

        Args:
            model_type: "origin_whisper" | "faster_whisper" | "fast_conformer"
            model_size: "tiny" | "base" | "small" | "medium" | "large" | "large-v3"
            device: "cpu" | "cuda"

        Returns:
            로드된 ASR 모델 인스턴스
        """
        # 캐시 키 생성
        key = f"{model_type}_{model_size}_{device}"

        with self._model_lock:
            if key not in self._models:
                logger.info(f"Loading new model: {key}")
                model = self._create_model(model_type, model_size, device)
                model.load_model()
                self._models[key] = model
            else:
                logger.info(f"Using cached model: {key}")

            return self._models[key]

    def _create_model(
        self,
        model_type: str,
        model_size: str,
        device: str
    ) -> ASRModelBase:
        """모델 인스턴스 생성"""
        if model_type == "faster_whisper":
            return FasterWhisperModel(model_size, device)
        elif model_type == "origin_whisper":
            return OriginWhisperModel(model_size, device)
        elif model_type == "fast_conformer":
            return FastConformerModel(model_size, device)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

    def clear_cache(self, model_type: Optional[str] = None):
        """
        모델 캐시 정리

        Args:
            model_type: 특정 타입만 정리 (None이면 전체)
        """
        with self._model_lock:
            if model_type:
                # 특정 타입만 정리
                keys_to_remove = [k for k in self._models.keys() if k.startswith(model_type)]
                for key in keys_to_remove:
                    self._models[key].unload_model()
                    del self._models[key]
                logger.info(f"Cleared cache for model type: {model_type}")
            else:
                # 전체 정리
                for model in self._models.values():
                    model.unload_model()
                self._models.clear()
                logger.info("Cleared all model cache")

# 전역 싱글톤 인스턴스
model_manager = ModelManager()
```

**사용 예시:**
```python
from app.core.models.manager import model_manager

# 모델 가져오기 (처음에는 로드, 이후에는 캐시에서 가져옴)
model = model_manager.get_model("faster_whisper", "large-v3", "cuda")

# 전사 수행
result = model.transcribe("/path/to/audio.mp3", "ko", {...})

# 캐시 정리 (필요시)
model_manager.clear_cache("faster_whisper")
```

---

### 6. Diarization Processor 클래스화

**파일**: `backend/app/core/processors/diarization.py`

**기존 코드 위치**: `woa/diarize.py:372-421` (diarization_process 함수)

```python
from typing import List, Tuple, Dict, Any
import torch
import librosa
import numpy as np
from pathlib import Path
from huggingface_hub import hf_hub_download
from woa.diarize import WeSpeakerResNet34, AgglomerativeClustering
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class DiarizationProcessor:
    """
    스피커 분별 처리기

    - 기존 woa/diarize.py::diarization_process 함수를 클래스화
    - 임베딩 모델 캐싱 지원
    - 배치 처리 가능
    """

    def __init__(self, hf_token: str = ""):
        self.hf_token = hf_token or settings.hf_token
        self.embedding_model = None
        self.cluster_model = AgglomerativeClustering()

    def load_embedding_model(self):
        """Embedding 모델 로딩 (한 번만 로드)"""
        if self.embedding_model is None:
            try:
                logger.info("Loading WeSpeaker embedding model...")

                # HuggingFace에서 모델 다운로드 (기존 woa/diarize.py:379)
                wespeaker_path = hf_hub_download(
                    repo_id="pyannote/wespeaker-voxceleb-resnet34-LM",
                    filename="pytorch_model.bin",
                    token=self.hf_token
                )

                # 모델 로드 (기존 woa/diarize.py:381-383)
                self.embedding_model = WeSpeakerResNet34.load_from_checkpoint(
                    wespeaker_path,
                    strict=False,
                    map_location='cpu'
                )
                self.embedding_model.eval()
                self.embedding_model.to('cpu')

                logger.info("WeSpeaker model loaded successfully")

            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise

    async def process_batch(
        self,
        results: List[Tuple[Dict, str]],
        min_speakers: int = 1,
        max_speakers: int = 5
    ) -> List[Tuple[Dict, str]]:
        """
        배치 Diarization 처리

        Args:
            results: [(transcription_result, audio_path), ...]
            min_speakers: 최소 화자 수
            max_speakers: 최대 화자 수

        Returns:
            화자 정보가 추가된 results
        """
        if not self.embedding_model:
            self.load_embedding_model()

        processed_results = []

        for result, audio_path in results:
            try:
                # 오디오 로딩 (기존 woa/diarize.py:385)
                audio, sr = librosa.load(audio_path, sr=16000, mono=True)

                # 각 세그먼트에서 임베딩 추출 (기존 woa/diarize.py:390-396)
                embeddings = []
                for segment in result["segments"]:
                    start, end = segment["start"], segment["end"]
                    audio_segment = audio[int(start * sr):int(end * sr)]

                    # 짧은 세그먼트 스킵
                    if len(audio_segment) < 160:  # 최소 10ms
                        embeddings.append(None)
                        continue

                    # Embedding 추출
                    audio_tensor = torch.Tensor(audio_segment).reshape(1, 1, -1)
                    with torch.no_grad():
                        embedding = self.embedding_model(audio_tensor)
                    embeddings.append(embedding.detach().cpu().numpy())

                # 클러스터링 (기존 woa/diarize.py:398-401)
                valid_embeddings = [e for e in embeddings if e is not None]
                if not valid_embeddings:
                    logger.warning(f"No valid embeddings for {audio_path}")
                    processed_results.append((result, audio_path))
                    continue

                embeddings_array = np.vstack(valid_embeddings)

                # AgglomerativeClustering (기존 woa/diarize.py::cluster 메서드)
                clusters = self.cluster_model.cluster(
                    embeddings_array,
                    min_clusters=min_speakers,
                    max_clusters=max_speakers
                )

                # 결과에 화자 정보 추가 (기존 woa/diarize.py:406-417)
                cluster_idx = 0
                for i, segment in enumerate(result["segments"]):
                    if embeddings[i] is not None:
                        speaker_id = f"발언자_{clusters[cluster_idx]}"
                        segment["speaker"] = speaker_id
                        cluster_idx += 1
                    else:
                        segment["speaker"] = "Unknown"

                processed_results.append((result, audio_path))
                logger.info(f"Diarization completed for {Path(audio_path).name}")

            except Exception as e:
                logger.error(f"Diarization failed for {audio_path}: {e}")
                # 실패해도 원본 결과 반환
                processed_results.append((result, audio_path))

        return processed_results

    def __del__(self):
        """리소스 정리"""
        if self.embedding_model is not None:
            del self.embedding_model
            torch.cuda.empty_cache()
```

**재사용 코드:**
- `woa/diarize.py::WeSpeakerResNet34` - 그대로 import
- `woa/diarize.py::AgglomerativeClustering` - 그대로 import

---

### 7. 결과 포맷터 유틸리티 복사

**파일**: `backend/app/core/processors/formatters.py`

**기존 코드**: `woa/utils.py` 전체를 복사하고 import 경로만 수정

```python
"""
결과 포맷팅 유틸리티
기존 woa/utils.py를 그대로 재사용
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from woa.utils import (
    get_writer,
    format_output_largev3,
    WriteTXT,
    WriteVTT,
    WriteSRT,
    WriteTSV,
    WriteJSON
)

# 기존 함수들을 그대로 export
__all__ = [
    "get_writer",
    "format_output_largev3",
    "save_results_to_files"
]

async def save_results_to_files(
    result: Dict[str, Any],
    audio_path: str,
    job_id: str,
    output_formats: List[str]
) -> Dict[str, str]:
    """
    전사 결과를 여러 형식으로 저장

    Args:
        result: 전사 결과 딕셔너리
        audio_path: 원본 오디오 파일 경로
        job_id: 작업 ID
        output_formats: 저장할 형식 리스트 (vtt, srt, json, txt, tsv)

    Returns:
        각 형식별 저장 경로 딕셔너리
    """
    from app.config import settings

    # 결과 저장 디렉토리 생성
    result_dir = settings.result_dir / job_id
    result_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 생성
    audio_basename = Path(audio_path).stem

    result_paths = {}
    writer_args = {"max_line_width": None, "max_line_count": None, "highlight_words": False}

    for fmt in output_formats:
        if fmt == "all":
            # 모든 형식으로 저장
            for single_fmt in ["json", "vtt", "srt", "txt", "tsv"]:
                writer = get_writer(single_fmt, str(result_dir))
                writer(result, audio_path, writer_args)
                result_paths[f"{single_fmt}_path"] = str(result_dir / f"{audio_basename}.{single_fmt}")
        else:
            # 특정 형식으로 저장
            writer = get_writer(fmt, str(result_dir))
            writer(result, audio_path, writer_args)
            result_paths[f"{fmt}_path"] = str(result_dir / f"{audio_basename}.{fmt}")

    return result_paths
```

---

## 테스트 계획

### 단위 테스트

**파일**: `backend/tests/unit/test_models.py`

```python
import pytest
from app.core.models.faster_whisper import FasterWhisperModel
from app.core.models.manager import ModelManager

def test_faster_whisper_loading():
    """FasterWhisper 모델 로딩 테스트"""
    model = FasterWhisperModel("tiny", "cpu")
    model.load_model()
    assert model.is_loaded == True
    model.unload_model()
    assert model.is_loaded == False

def test_model_manager_singleton():
    """ModelManager 싱글톤 패턴 테스트"""
    manager1 = ModelManager()
    manager2 = ModelManager()
    assert manager1 is manager2

def test_model_manager_caching():
    """모델 캐싱 테스트"""
    manager = ModelManager()
    model1 = manager.get_model("faster_whisper", "tiny", "cpu")
    model2 = manager.get_model("faster_whisper", "tiny", "cpu")
    assert model1 is model2  # 같은 인스턴스
```

### 통합 테스트

**파일**: `backend/tests/integration/test_transcription.py`

```python
import pytest
from app.core.models.manager import model_manager

@pytest.mark.asyncio
async def test_full_transcription_pipeline():
    """전체 전사 파이프라인 테스트"""
    # 테스트 오디오 파일 필요
    test_audio = "tests/fixtures/test_audio.wav"

    # 모델 가져오기
    model = model_manager.get_model("faster_whisper", "tiny", "cpu")

    # 전사 수행
    result = model.transcribe(
        test_audio,
        "ko",
        {"beam_size": 5, "temperature": 0}
    )

    # 검증
    assert "segments" in result
    assert len(result["segments"]) > 0
```

---

## 마이그레이션 체크리스트

### 코드 작성
- [ ] `ASRModelBase` 추상 클래스 작성
- [ ] `FasterWhisperModel` 구현
- [ ] `OriginWhisperModel` 구현
- [ ] `FastConformerModel` 구현
- [ ] `ModelManager` 싱글톤 구현
- [ ] `DiarizationProcessor` 클래스화
- [ ] `formatters.py` 유틸리티 복사

### 테스트
- [ ] 각 모델 클래스 단위 테스트
- [ ] ModelManager 싱글톤 테스트
- [ ] 모델 캐싱 동작 검증
- [ ] GPU 메모리 누수 테스트
- [ ] 통합 테스트 (전체 파이프라인)

### 검증
- [ ] 기존 Gradio 앱과 결과 비교 (동일한 입력에 대해 동일한 출력)
- [ ] 성능 측정 (모델 캐싱 전후 비교)
- [ ] 메모리 사용량 모니터링
- [ ] 동시 요청 처리 테스트

---

## 성공 기준

1. **기능성**
   - 3개 모델 모두 정상 동작
   - 기존 Gradio 앱과 동일한 전사 품질

2. **성능**
   - 첫 요청: 모델 로딩 포함
   - 이후 요청: 모델 재사용으로 3-5배 빠른 응답
   - GPU 메모리 누수 없음

3. **코드 품질**
   - 타입 힌팅 100% 적용
   - 테스트 커버리지 70% 이상
   - 로깅 완비

---

## 보안 고려사항

### FastConformer 모델
- 현재 `ast.literal_eval()` 사용 중 (보안상 권장하지 않음)
- Docker 컨테이너가 신뢰할 수 있는 환경이므로 현재는 유지
- **향후 개선**: `docker/run_nemo.py`를 JSON 출력으로 수정 권장

### 입력 검증
- 모든 사용자 입력 (audio_path, params)에 대한 검증 필요
- 경로 탐색 공격 방지

---

## 다음 단계 (Phase 3)

Phase 2 완료 후:
- 전사 API 엔드포인트 구현 (`/api/v1/transcribe`)
- 작업 상태 조회 API (`/api/v1/jobs/{job_id}`)
- BackgroundTasks를 사용한 비동기 처리
- 진행률 추적 메커니즘

---

## 참고 자료

### 기존 코드 파일
- `woa/events.py` - 3개 모델의 전사 로직
- `woa/diarize.py` - 스피커 분별 로직
- `woa/utils.py` - 결과 포맷팅 유틸리티
- `docker/run_nemo.py` - FastConformer Docker 실행 스크립트

### 새로 생성할 파일
- `backend/app/core/models/base.py`
- `backend/app/core/models/faster_whisper.py`
- `backend/app/core/models/whisper_original.py`
- `backend/app/core/models/fast_conformer.py`
- `backend/app/core/models/manager.py`
- `backend/app/core/processors/diarization.py`
- `backend/app/core/processors/formatters.py`
- `backend/tests/unit/test_models.py`
- `backend/tests/integration/test_transcription.py`

---

**마지막 업데이트**: 2026-02-13
**작성자**: Claude Code + Happy
