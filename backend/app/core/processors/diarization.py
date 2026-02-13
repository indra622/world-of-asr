"""
스피커 분별(Diarization) 프로세서

기존 woa/diarize.py::diarization_process 함수를 클래스 기반으로 리팩토링
"""
from typing import Dict, Any, Optional
import numpy as np
import torch
import librosa
from huggingface_hub import hf_hub_download
import logging

# 기존 woa/diarize.py의 클래스들을 재사용
from woa.diarize import WeSpeakerResNet34, AgglomerativeClustering

logger = logging.getLogger(__name__)


class DiarizationProcessor:
    """
    스피커 분별 프로세서

    WeSpeaker ResNet34 임베딩 모델과 계층적 군집화를 사용하여
    전사 결과에 화자 레이블을 추가합니다.

    **사용 예시:**
    ```python
    from app.core.processors.diarization import DiarizationProcessor

    # 프로세서 생성
    processor = DiarizationProcessor(hf_token="your_token")

    # 임베딩 모델 로드
    processor.load_embedding_model()

    # 스피커 분별 수행
    result = processor.process(
        audio_path="/path/to/audio.mp3",
        transcription_result=transcription_result,
        min_speakers=2,
        max_speakers=15
    )

    # 메모리 정리
    processor.unload_model()
    ```
    """

    def __init__(self, hf_token: Optional[str] = None):
        """
        Args:
            hf_token: HuggingFace Hub 토큰 (웨이트 다운로드용)
        """
        self.hf_token = hf_token
        self.embedding_model: Optional[WeSpeakerResNet34] = None
        self.is_loaded = False

    def load_embedding_model(self) -> None:
        """
        WeSpeaker 임베딩 모델 로딩

        기존 코드: woa/diarize.py:379-383
        """
        try:
            logger.info("Loading WeSpeaker embedding model")

            # HuggingFace Hub에서 웨이트 다운로드 (기존 woa/diarize.py:379)
            wespeaker_checkpoint = hf_hub_download(
                repo_id="pyannote/wespeaker-voxceleb-resnet34-LM",
                filename="pytorch_model.bin",
                token=self.hf_token
            )

            # 모델 로드 (기존 woa/diarize.py:381-383)
            # NOTE: strict=False는 체크포인트와 모델 구조 간 불일치를 허용합니다
            self.embedding_model = WeSpeakerResNet34.load_from_checkpoint(
                wespeaker_checkpoint,
                strict=False,
                map_location='cpu'
            )
            # 추론 모드로 설정 (학습하지 않음)
            self.embedding_model.to('cpu')

            self.is_loaded = True
            logger.info("WeSpeaker model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load WeSpeaker model: {e}")
            raise

    def process(
        self,
        audio_path: str,
        transcription_result: Dict[str, Any],
        min_speakers: int = 2,
        max_speakers: int = 15
    ) -> Dict[str, Any]:
        """
        스피커 분별 수행

        기존 코드: woa/diarize.py:372-421

        Args:
            audio_path: 오디오 파일 경로
            transcription_result: ASR 전사 결과 (segments 포함)
            min_speakers: 최소 화자 수
            max_speakers: 최대 화자 수

        Returns:
            화자 레이블이 추가된 전사 결과
            {
                "segments": [
                    {
                        "start": float,
                        "end": float,
                        "text": str,
                        "speaker": "발언자_0" | "발언자_1" | ...
                    },
                    ...
                ]
            }

        Raises:
            ValueError: segments 수와 clusters 수가 불일치할 경우
        """
        if not self.is_loaded:
            self.load_embedding_model()

        try:
            logger.info(f"Starting diarization for {audio_path}")

            # 오디오 로드 (기존 woa/diarize.py:385)
            audio, sr = librosa.load(audio_path, sr=16000, mono=True)

            # 각 세그먼트의 임베딩 추출 (기존 woa/diarize.py:388-396)
            embeddings = []
            segments = transcription_result.get("segments", [])

            for segment in segments:
                start, end = segment["start"], segment["end"]

                # 오디오 세그먼트 추출
                audio_segment = audio[int(start * sr):int(end * sr)]
                audio_segment = torch.Tensor(audio_segment).reshape(1, 1, -1)

                # 임베딩 계산
                embedding = self.embedding_model(audio_segment)
                embeddings.append(embedding.detach().numpy())

            # 군집화 수행 (기존 woa/diarize.py:398-401)
            cluster_model = AgglomerativeClustering()
            cluster_model.set_num_clusters(
                len(embeddings),
                min_clusters=min_speakers,
                max_clusters=max_speakers
            )

            clusters = cluster_model.cluster(np.vstack(embeddings))
            clusters = list(clusters)

            # 검증 (기존 woa/diarize.py:403-404)
            if len(segments) != len(clusters):
                error_msg = (
                    f"Mismatch: {len(segments)} segments vs {len(clusters)} clusters"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            # 화자 레이블 추가 (기존 woa/diarize.py:406-417)
            output = {
                'segments': [
                    {
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': segment['text'],
                        'speaker': f"발언자_{clusters.pop(0)}",
                    }
                    for segment in segments
                ],
            }

            logger.info(
                f"Diarization completed: {len(segments)} segments, "
                f"{len(set([s['speaker'] for s in output['segments']]))} speakers"
            )
            return output

        except Exception as e:
            logger.error(f"Diarization failed for {audio_path}: {e}")
            raise

    def unload_model(self) -> None:
        """
        임베딩 모델 메모리 해제

        기존 코드: woa/diarize.py:419
        """
        if self.embedding_model is not None:
            logger.info("Unloading WeSpeaker embedding model")
            del self.embedding_model
            self.embedding_model = None
            self.is_loaded = False
            logger.debug("WeSpeaker model unloaded")

    def __enter__(self):
        """컨텍스트 매니저 진입"""
        if not self.is_loaded:
            self.load_embedding_model()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        self.unload_model()
