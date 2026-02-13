"""
pytest 공통 설정 및 fixture
"""
import pytest
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# woa 모듈도 추가 (기존 Gradio 앱 모듈) - 하지만 우선순위를 낮춤
woa_path = project_root.parent / "woa"
if woa_path.exists():
    sys.path.append(str(woa_path.parent))  # insert 대신 append 사용


@pytest.fixture
def sample_transcription_result():
    """샘플 전사 결과"""
    return {
        "segments": [
            {
                "start": 0.0,
                "end": 2.5,
                "text": " Hello world",
            },
            {
                "start": 2.5,
                "end": 5.0,
                "text": " How are you?",
            },
            {
                "start": 5.0,
                "end": 7.5,
                "text": " I'm doing great!",
            },
        ]
    }


@pytest.fixture
def sample_transcription_with_words():
    """단어 타임스탬프가 포함된 샘플 전사 결과"""
    return {
        "segments": [
            {
                "start": 0.0,
                "end": 2.0,
                "text": " Hello world",
                "words": [
                    {"word": " Hello", "start": 0.0, "end": 0.5},
                    {"word": " world", "start": 0.6, "end": 2.0},
                ]
            },
            {
                "start": 2.0,
                "end": 4.0,
                "text": " How are you?",
                "words": [
                    {"word": " How", "start": 2.0, "end": 2.3},
                    {"word": " are", "start": 2.4, "end": 2.7},
                    {"word": " you?", "start": 2.8, "end": 4.0},
                ]
            },
        ]
    }


@pytest.fixture
def sample_transcription_with_speakers():
    """화자 정보가 포함된 샘플 전사 결과"""
    return {
        "segments": [
            {
                "start": 0.0,
                "end": 2.0,
                "text": " Hello",
                "speaker": "발언자_0"
            },
            {
                "start": 2.0,
                "end": 4.0,
                "text": " Hi there",
                "speaker": "발언자_1"
            },
            {
                "start": 4.0,
                "end": 6.0,
                "text": " How are you?",
                "speaker": "발언자_0"
            },
        ]
    }


@pytest.fixture
def mock_audio_file(tmp_path):
    """Mock 오디오 파일 경로"""
    audio_path = tmp_path / "test_audio.mp3"
    audio_path.touch()  # 빈 파일 생성
    return str(audio_path)


@pytest.fixture
def reset_model_manager_cache():
    """각 테스트 전후로 ModelManager 캐시 초기화 (옵션)"""
    # autouse=False로 변경하여 필요한 테스트에서만 사용
    try:
        from app.core.models.manager import model_manager

        # 테스트 전 캐시 정리
        model_manager.clear_cache()

        yield

        # 테스트 후 캐시 정리
        model_manager.clear_cache()
    except ImportError:
        # 의존성이 없을 때는 skip
        yield
