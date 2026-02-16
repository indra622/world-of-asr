"""
FastConformer 모델 래퍼 (Docker 기반)

기존 woa/events.py::fastconformer_process 함수를 클래스 기반으로 리팩토링
"""
from typing import Dict, Any, Optional
import json
import docker
from app.core.models.base import ASRModelBase
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class FastConformerModel(ASRModelBase):
    """
    FastConformer (NeMo) 모델 래퍼 - Docker 기반

    NeMo FastConformer 모델을 Docker 컨테이너에서 실행
    기존 Gradio 앱의 fastconformer_process 로직을 그대로 재사용
    """

    def __init__(self, model_size: str, device: str):
        """
        Args:
            model_size: 모델 크기 (NeMo 모델의 경우 크기가 고정될 수 있음)
            device: 디바이스 (Docker 컨테이너 내부에서 처리)
        """
        super().__init__(model_size, device)
        self.docker_client = None
        self.container = None

    def load_model(self) -> None:
        """
        Docker 컨테이너 연결

        기존 코드: woa/events.py:220-225
        """
        try:
            logger.info("Connecting to FastConformer Docker container")

            # 환경 변수 확인 (기존 woa/events.py:220-221)
            container_id = settings.container_id
            if not container_id:
                raise ValueError(
                    "CONTAINER_ID environment variable not set. "
                    "Please set it in .env file or environment."
                )

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
        """
        전사 수행 - Docker exec를 통해 NeMo 실행

        기존 코드: woa/events.py:227-236

        Args:
            audio_path: 오디오 파일 경로
            language: 언어 힌트 (FastConformer는 사용하지 않을 수 있음)
            params: 전사 파라미터 (FastConformer는 고정 파라미터 사용)

        Returns:
            전사 결과 딕셔너리
        """
        if not self.is_loaded:
            self.load_model()

        try:
            logger.info(f"Transcribing with FastConformer (Docker): {audio_path}")

            # Docker exec 실행 (기존 woa/events.py:234)
            # Pass argv as list to avoid shell parsing issues
            result = self.container.exec_run(
                cmd=["python", "run_nemo.py", audio_path],
                stderr=False,
            )

            # 결과 파싱 (기존 woa/events.py:227-230, 235)
            output = result.output.decode("utf-8")

            # JSON으로 파싱 시도
            try:
                parsed_result = json.loads(output)
                logger.info("FastConformer result parsed as JSON")
            except json.JSONDecodeError:
                # 기존 방식 사용 - ast.literal_eval 사용
                # SECURITY NOTE: ast.literal_eval은 신뢰할 수 없는 입력에 사용하면 안 됩니다.
                # 그러나 Docker 컨테이너는 우리가 통제하는 환경이므로 안전합니다.
                # 향후 개선: docker/run_nemo.py를 JSON 출력으로 수정 권장
                import ast
                logger.warning(
                    "Using ast.literal_eval for parsing Docker output. "
                    "Consider migrating docker/run_nemo.py to JSON output."
                )
                parsed_result = ast.literal_eval(output)

            # 포맷 변환 (기존 woa/events.py:236)
            # parsed_result는 [[result], filename] 형태
            transcription_result = parsed_result[0][0]

            logger.info("FastConformer completed")
            return transcription_result

        except Exception as e:
            logger.error(f"FastConformer failed for {audio_path}: {e}")
            raise

    def unload_model(self) -> None:
        """
        Docker 연결 종료

        Docker 클라이언트를 닫습니다.
        """
        if self.docker_client is not None:
            logger.info("Closing Docker client connection")
            self.docker_client.close()
            self.docker_client = None
            self.container = None
            self.is_loaded = False
            logger.debug("Docker client closed")
