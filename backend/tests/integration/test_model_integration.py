"""
Phase 2 모델 통합 테스트

전체 전사 파이프라인 통합 테스트
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from app.core.models.manager import ModelManager
from app.core.processors.diarization import DiarizationProcessor
from app.core.processors.formatters import get_writer


class TestTranscriptionPipeline:
    """전사 파이프라인 통합 테스트"""

    @patch('app.core.models.manager.FasterWhisperModel')
    def test_end_to_end_transcription_without_diarization(
        self, mock_faster_whisper_class, tmp_path
    ):
        """전사 전체 플로우 (스피커 분별 없음)"""

        # Mock 모델 설정
        mock_model = Mock()
        mock_faster_whisper_class.return_value = mock_model

        # Mock 전사 결과
        mock_transcription_result = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": " Hello world"},
                {"start": 2.5, "end": 5.0, "text": " How are you?"},
            ]
        }
        mock_model.transcribe.return_value = mock_transcription_result

        # 1. ModelManager로 모델 가져오기
        manager = ModelManager()
        manager.clear_cache()

        model = manager.get_model("faster_whisper", "large-v3", "cuda", "float16")

        # 2. 전사 수행
        audio_path = "test_audio.mp3"
        language = "ko"
        params = {"beam_size": 5, "temperature": 0}

        result = model.transcribe(audio_path, language, params)

        # 3. 결과 검증
        assert "segments" in result
        assert len(result["segments"]) == 2
        assert result["segments"][0]["text"] == " Hello world"

        # 4. 포맷터로 결과 저장
        output_dir = str(tmp_path)
        writer = get_writer("vtt", output_dir)
        output_path = writer(result, audio_path, {})

        # 5. 파일 생성 확인
        assert os.path.exists(output_path)

        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "WEBVTT" in content
        assert "Hello world" in content

    @patch('app.core.processors.diarization.WeSpeakerResNet34')
    @patch('app.core.processors.diarization.hf_hub_download')
    @patch('app.core.processors.diarization.librosa')
    def test_transcription_with_diarization(
        self, mock_librosa, mock_hf_download, mock_wespeaker_class, tmp_path
    ):
        """전사 + 스피커 분별 통합 플로우"""

        # Mock 오디오 로드
        import numpy as np
        mock_audio = np.random.randn(16000 * 10)  # 10초 오디오
        mock_librosa.load.return_value = (mock_audio, 16000)

        # Mock WeSpeaker 모델
        mock_embedding_model = Mock()
        mock_wespeaker_class.load_from_checkpoint.return_value = mock_embedding_model

        # Mock 임베딩 출력
        import torch
        mock_embedding = torch.randn(1, 256)
        mock_embedding_model.return_value = mock_embedding

        # 전사 결과 (스피커 정보 없음)
        transcription_result = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": " Hello"},
                {"start": 2.0, "end": 4.0, "text": " Hi there"},
                {"start": 4.0, "end": 6.0, "text": " How are you?"},
            ]
        }

        # DiarizationProcessor 생성 및 처리
        processor = DiarizationProcessor(hf_token="test_token")

        # Mock AgglomerativeClustering
        with patch('app.core.processors.diarization.AgglomerativeClustering') as mock_cluster_class:
            mock_cluster = Mock()
            mock_cluster_class.return_value = mock_cluster

            # 화자 클러스터 결과 (3개 세그먼트 -> 2명의 화자)
            mock_cluster.cluster.return_value = np.array([0, 1, 0])

            # 스피커 분별 수행
            result = processor.process(
                audio_path="test_audio.mp3",
                transcription_result=transcription_result,
                min_speakers=2,
                max_speakers=5
            )

        # 결과 검증
        assert "segments" in result
        assert len(result["segments"]) == 3

        # 화자 레이블 확인
        assert "speaker" in result["segments"][0]
        assert result["segments"][0]["speaker"] == "발언자_0"
        assert result["segments"][1]["speaker"] == "발언자_1"
        assert result["segments"][2]["speaker"] == "발언자_0"

        # 결과를 VTT로 저장
        output_dir = str(tmp_path)
        writer = get_writer("vtt", output_dir)
        output_path = writer(result, "test_audio.mp3", {})

        # 파일 검증
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 화자 레이블이 포함되었는지 확인
        assert "[발언자_0]" in content
        assert "[발언자_1]" in content

    @patch('app.core.models.manager.FasterWhisperModel')
    def test_multiple_format_export(self, mock_faster_whisper_class, tmp_path):
        """여러 포맷으로 동시 저장"""

        # Mock 모델 설정
        mock_model = Mock()
        mock_faster_whisper_class.return_value = mock_model

        # Mock 전사 결과
        mock_result = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": " Test transcription"},
            ]
        }
        mock_model.transcribe.return_value = mock_result

        # 모델 가져오기
        manager = ModelManager()
        manager.clear_cache()
        model = manager.get_model("faster_whisper", "large-v3", "cuda")

        # 전사 수행
        result = model.transcribe("test.mp3", "ko", {})

        # 모든 포맷으로 저장
        output_dir = str(tmp_path)
        writer = get_writer("all", output_dir)
        output_paths = writer(result, "test.mp3", {})

        # 5개 파일 생성 확인
        assert len(output_paths) == 5

        # 각 포맷 파일 존재 확인
        extensions = ["txt", "vtt", "srt", "tsv", "json"]
        for ext in extensions:
            file_path = tmp_path / f"test.{ext}"
            assert os.path.exists(file_path), f"{ext} file not created"

    @patch('app.core.models.manager.FasterWhisperModel')
    @patch('app.core.models.manager.OriginWhisperModel')
    def test_model_switching(self, mock_origin_class, mock_faster_class):
        """모델 전환 테스트"""

        # Mock 모델들
        mock_faster = Mock()
        mock_origin = Mock()

        mock_faster_class.return_value = mock_faster
        mock_origin_class.return_value = mock_origin

        mock_faster_result = {"segments": [{"start": 0, "end": 1, "text": "Faster"}]}
        mock_origin_result = {"segments": [{"start": 0, "end": 1, "text": "Origin"}]}

        mock_faster.transcribe.return_value = mock_faster_result
        mock_origin.transcribe.return_value = mock_origin_result

        manager = ModelManager()
        manager.clear_cache()

        # FasterWhisper 사용
        faster_model = manager.get_model("faster_whisper", "large-v3", "cuda")
        result1 = faster_model.transcribe("test.mp3", "ko", {})
        assert result1["segments"][0]["text"] == "Faster"

        # Origin Whisper로 전환
        origin_model = manager.get_model("origin_whisper", "large-v3", "cuda")
        result2 = origin_model.transcribe("test.mp3", "ko", {})
        assert result2["segments"][0]["text"] == "Origin"

        # 캐시 정보 확인
        cache_info = manager.get_cache_info()
        assert cache_info["faster_whisper"] == 1
        assert cache_info["origin_whisper"] == 1
        assert cache_info["total"] == 2

    @patch('app.core.models.manager.FasterWhisperModel')
    def test_model_context_manager(self, mock_faster_whisper_class):
        """모델 컨텍스트 매니저 사용"""

        mock_model = Mock()
        mock_faster_whisper_class.return_value = mock_model

        mock_result = {"segments": [{"start": 0, "end": 1, "text": "Test"}]}
        mock_model.transcribe.return_value = mock_result

        manager = ModelManager()
        manager.clear_cache()

        # with 구문으로 모델 사용
        model = manager.get_model("faster_whisper", "large-v3", "cuda")

        with model:
            result = model.transcribe("test.mp3", "ko", {})
            assert result["segments"][0]["text"] == "Test"

        # __exit__ 호출로 unload_model이 호출되어야 함
        # 하지만 ModelManager가 캐시를 관리하므로 실제로는 유지됨
        # 이는 설계상 의도된 동작


class TestErrorHandling:
    """에러 처리 통합 테스트"""

    def test_unknown_model_type(self):
        """존재하지 않는 모델 타입"""
        manager = ModelManager()

        with pytest.raises(ValueError, match="Unknown model type"):
            manager.get_model("nonexistent_model", "large-v3", "cuda")

    @patch('app.core.processors.diarization.WeSpeakerResNet34')
    @patch('app.core.processors.diarization.hf_hub_download')
    @patch('app.core.processors.diarization.librosa')
    def test_diarization_segment_mismatch(
        self, mock_librosa, mock_hf_download, mock_wespeaker_class
    ):
        """세그먼트와 클러스터 수 불일치 에러"""

        import numpy as np
        import torch

        mock_audio = np.random.randn(16000 * 5)
        mock_librosa.load.return_value = (mock_audio, 16000)

        mock_embedding_model = Mock()
        mock_wespeaker_class.load_from_checkpoint.return_value = mock_embedding_model
        mock_embedding_model.return_value = torch.randn(1, 256)

        transcription_result = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": " Test"},
            ]
        }

        processor = DiarizationProcessor(hf_token="test_token")

        with patch('app.core.processors.diarization.AgglomerativeClustering') as mock_cluster_class:
            mock_cluster = Mock()
            mock_cluster_class.return_value = mock_cluster

            # 잘못된 클러스터 수 반환 (1개 세그먼트인데 2개 클러스터)
            mock_cluster.cluster.return_value = np.array([0, 1])

            # ValueError 발생 예상
            with pytest.raises(ValueError, match="Mismatch"):
                processor.process(
                    "test.mp3",
                    transcription_result,
                    min_speakers=2,
                    max_speakers=5
                )


class TestMemoryManagement:
    """메모리 관리 테스트"""

    @patch('app.core.models.manager.FasterWhisperModel')
    def test_cache_clear_releases_models(self, mock_faster_whisper_class):
        """캐시 정리 시 모델 언로드"""

        mock_model = Mock()
        mock_faster_whisper_class.return_value = mock_model

        manager = ModelManager()
        manager.clear_cache()

        # 모델 로드
        model = manager.get_model("faster_whisper", "large-v3", "cuda")

        # 캐시 확인
        cache_info = manager.get_cache_info()
        assert cache_info["total"] == 1

        # 캐시 정리
        manager.clear_cache("faster_whisper")

        # unload_model 호출 확인
        mock_model.unload_model.assert_called_once()

        # 캐시 비어있음 확인
        cache_info = manager.get_cache_info()
        assert cache_info["total"] == 0
