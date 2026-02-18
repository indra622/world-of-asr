"""
ModelManager 단위 테스트
"""
import pytest
import threading
from unittest.mock import Mock, patch, MagicMock
from app.core.models.manager import ModelManager, model_manager
from app.core.models.base import ASRModelBase


class TestModelManager:
    """ModelManager 싱글톤 테스트"""

    def test_singleton_pattern(self):
        """싱글톤 패턴 검증 - 항상 같은 인스턴스 반환"""
        manager1 = ModelManager()
        manager2 = ModelManager()

        assert manager1 is manager2
        assert id(manager1) == id(manager2)

    def test_global_instance(self):
        """전역 인스턴스가 싱글톤과 동일"""
        manager = ModelManager()

        assert model_manager is manager

    def test_thread_safety(self):
        """멀티스레드 환경에서 싱글톤 보장"""
        instances = []

        def create_manager():
            instances.append(ModelManager())

        threads = [threading.Thread(target=create_manager) for _ in range(10)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 모든 인스턴스가 동일해야 함
        first_instance = instances[0]
        assert all(instance is first_instance for instance in instances)

    @patch('app.core.models.manager.FasterWhisperModel')
    def test_get_model_caching(self, mock_faster_whisper_class):
        """모델 캐싱 동작 검증"""
        # Mock 모델 인스턴스
        mock_model = Mock(spec=ASRModelBase)
        mock_faster_whisper_class.return_value = mock_model

        manager = ModelManager()
        manager.clear_cache()  # 테스트 전 캐시 정리

        # 첫 번째 호출 - 새로 로드
        model1 = manager.get_model("faster_whisper", "large-v3", "cuda", "float16")

        # load_model이 호출되었는지 확인
        mock_model.load_model.assert_called_once()

        # 두 번째 호출 - 캐시에서 가져옴
        model2 = manager.get_model("faster_whisper", "large-v3", "cuda", "float16")

        # 같은 인스턴스여야 함
        assert model1 is model2

        # load_model은 한 번만 호출되어야 함
        assert mock_model.load_model.call_count == 1

    @patch('app.core.models.manager.FasterWhisperModel')
    @patch('app.core.models.manager.OriginWhisperModel')
    def test_different_models_cached_separately(
        self, mock_origin_class, mock_faster_class
    ):
        """서로 다른 모델은 별도로 캐싱"""
        mock_faster_model = Mock(spec=ASRModelBase)
        mock_origin_model = Mock(spec=ASRModelBase)

        mock_faster_class.return_value = mock_faster_model
        mock_origin_class.return_value = mock_origin_model

        manager = ModelManager()
        manager.clear_cache()

        # 두 가지 다른 모델 로드
        model1 = manager.get_model("faster_whisper", "large-v3", "cuda", "float16")
        model2 = manager.get_model("origin_whisper", "large-v3", "cuda")

        # 서로 다른 인스턴스
        assert model1 is not model2
        assert model1 is mock_faster_model
        assert model2 is mock_origin_model

    @patch('app.core.models.manager.FasterWhisperModel')
    def test_cache_key_includes_compute_type(self, mock_faster_whisper_class):
        """compute_type이 다르면 별도 캐싱"""
        mock_model1 = Mock(spec=ASRModelBase)
        mock_model2 = Mock(spec=ASRModelBase)

        # 각 호출마다 다른 인스턴스 반환
        mock_faster_whisper_class.side_effect = [mock_model1, mock_model2]

        manager = ModelManager()
        manager.clear_cache()

        model_float16 = manager.get_model("faster_whisper", "large-v3", "cuda", "float16")
        model_int8 = manager.get_model("faster_whisper", "large-v3", "cuda", "int8")

        # 서로 다른 인스턴스여야 함
        assert model_float16 is not model_int8

    @patch('app.core.models.manager.FasterWhisperModel')
    def test_clear_cache_specific_type(self, mock_faster_whisper_class):
        """특정 타입 캐시만 정리"""
        mock_model = Mock(spec=ASRModelBase)
        mock_faster_whisper_class.return_value = mock_model

        manager = ModelManager()
        manager.clear_cache()

        # 모델 로드
        manager.get_model("faster_whisper", "large-v3", "cuda", "float16")

        # 캐시 정보 확인
        info = manager.get_cache_info()
        assert info["faster_whisper"] == 1
        assert info["total"] == 1

        # faster_whisper 캐시만 정리
        manager.clear_cache("faster_whisper")

        # unload_model이 호출되었는지 확인
        mock_model.unload_model.assert_called_once()

        # 캐시가 비었는지 확인
        info = manager.get_cache_info()
        assert info["faster_whisper"] == 0
        assert info["total"] == 0

    @patch('app.core.models.manager.FasterWhisperModel')
    @patch('app.core.models.manager.OriginWhisperModel')
    def test_clear_all_cache(self, mock_origin_class, mock_faster_class):
        """전체 캐시 정리"""
        mock_faster = Mock(spec=ASRModelBase)
        mock_origin = Mock(spec=ASRModelBase)

        mock_faster_class.return_value = mock_faster
        mock_origin_class.return_value = mock_origin

        manager = ModelManager()
        manager.clear_cache()

        # 두 모델 로드
        manager.get_model("faster_whisper", "large-v3", "cuda", "float16")
        manager.get_model("origin_whisper", "large-v3", "cuda")

        info = manager.get_cache_info()
        assert info["total"] == 2

        # 전체 캐시 정리
        manager.clear_cache()

        # 두 모델 모두 unload되었는지 확인
        mock_faster.unload_model.assert_called_once()
        mock_origin.unload_model.assert_called_once()

        # 캐시가 비었는지 확인
        info = manager.get_cache_info()
        assert info["total"] == 0

    def test_get_cache_info(self):
        """캐시 정보 조회"""
        manager = ModelManager()
        manager.clear_cache()

        info = manager.get_cache_info()

        # 초기 상태
        assert info["origin_whisper"] == 0
        assert info["faster_whisper"] == 0
        assert info["fast_conformer"] == 0
        assert info["hf_auto_asr"] == 0
        assert info["total"] == 0

    @patch('app.core.models.manager.HFAutoASRModel')
    def test_hf_auto_asr_model_creation(self, mock_hf_auto_asr_class):
        mock_model = Mock(spec=ASRModelBase)
        mock_hf_auto_asr_class.return_value = mock_model

        manager = ModelManager()
        manager.clear_cache()

        model = manager.get_model("hf_auto_asr", "openai/whisper-small", "cpu")

        mock_hf_auto_asr_class.assert_called_once_with("openai/whisper-small", "cpu")
        mock_model.load_model.assert_called_once()
        assert model is mock_model

    def test_unknown_model_type_raises_error(self):
        """알 수 없는 모델 타입은 ValueError 발생"""
        manager = ModelManager()

        with pytest.raises(ValueError, match="Unknown model type"):
            manager.get_model("unknown_model", "large-v3", "cuda")

    @patch('app.core.models.manager.FastConformerModel')
    def test_fast_conformer_model_creation(self, mock_fast_conformer_class):
        """FastConformer 모델 생성 검증"""
        mock_model = Mock(spec=ASRModelBase)
        mock_fast_conformer_class.return_value = mock_model

        manager = ModelManager()
        manager.clear_cache()

        model = manager.get_model("fast_conformer", "stt_en_conformer_ctc_large", "cuda")

        # FastConformerModel이 올바른 파라미터로 생성되었는지 확인
        mock_fast_conformer_class.assert_called_once_with(
            "stt_en_conformer_ctc_large", "cuda"
        )

        # load_model이 호출되었는지 확인
        mock_model.load_model.assert_called_once()
