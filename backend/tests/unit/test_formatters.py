"""
전사 결과 포맷터 단위 테스트
"""
import pytest
import os
import json
import tempfile
from app.core.processors.formatters import (
    format_timestamp,
    WriteTXT,
    WriteVTT,
    WriteSRT,
    WriteTSV,
    WriteJSON,
    get_writer,
    format_output_largev3
)


class TestFormatTimestamp:
    """format_timestamp 함수 테스트"""

    def test_basic_timestamp(self):
        """기본 타임스탬프 포맷"""
        result = format_timestamp(83.456)
        assert result == "01:23.456"

    def test_with_hours(self):
        """1시간 이상인 경우"""
        result = format_timestamp(3723.456)
        assert result == "01:02:03.456"

    def test_always_include_hours(self):
        """항상 시간 포함"""
        result = format_timestamp(83.456, always_include_hours=True)
        assert result == "00:01:23.456"

    def test_decimal_marker(self):
        """소수점 구분자 변경 (SRT용)"""
        result = format_timestamp(83.456, decimal_marker=",")
        assert result == "01:23,456"

    def test_zero_seconds(self):
        """0초"""
        result = format_timestamp(0)
        assert result == "00:00.000"

    def test_milliseconds_rounding(self):
        """밀리초 반올림"""
        result = format_timestamp(1.2345)
        assert result == "00:01.234"  # 1234.5ms -> 1234ms


class TestWriteTXT:
    """WriteTXT 포맷터 테스트"""

    def test_write_txt(self, tmp_path):
        """TXT 파일 생성"""
        result = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": " Hello world"},
                {"start": 2.0, "end": 4.0, "text": " How are you?"},
            ]
        }

        writer = WriteTXT(str(tmp_path))
        output_path = writer(result, "test_audio.mp3", {})

        # 파일 존재 확인
        assert os.path.exists(output_path)
        assert output_path == str(tmp_path / "test_audio.txt")

        # 내용 확인
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "Hello world" in content
        assert "How are you?" in content


class TestWriteVTT:
    """WriteVTT 포맷터 테스트"""

    def test_write_vtt(self, tmp_path):
        """VTT 파일 생성"""
        result = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": " Hello"},
                {"start": 2.5, "end": 5.0, "text": " World"},
            ]
        }

        writer = WriteVTT(str(tmp_path))
        output_path = writer(result, "test.mp3", {})

        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()

        # VTT 헤더 확인
        assert "WEBVTT" in content

        # 타임스탬프 확인
        assert "00:00.000 --> 00:02.500" in content
        assert "00:02.500 --> 00:05.000" in content

        # 텍스트 확인
        assert "Hello" in content
        assert "World" in content

    def test_vtt_with_speaker(self, tmp_path):
        """화자 정보가 포함된 VTT"""
        result = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": " Hello", "speaker": "발언자_0"},
                {"start": 2.0, "end": 4.0, "text": " Hi", "speaker": "발언자_1"},
            ]
        }

        writer = WriteVTT(str(tmp_path))
        output_path = writer(result, "test.mp3", {})

        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 화자 레이블 확인
        assert "[발언자_0]" in content
        assert "[발언자_1]" in content


class TestWriteSRT:
    """WriteSRT 포맷터 테스트"""

    def test_write_srt(self, tmp_path):
        """SRT 파일 생성"""
        result = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": " First line"},
                {"start": 2.0, "end": 4.0, "text": " Second line"},
            ]
        }

        writer = WriteSRT(str(tmp_path))
        output_path = writer(result, "test.mp3", {})

        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()

        # SRT 인덱스 확인
        assert "1\n" in content
        assert "2\n" in content

        # 타임스탬프 포맷 확인 (항상 시간 포함, 쉼표 사용)
        assert "00:00:00,000 --> 00:00:02,000" in content
        assert "00:00:02,000 --> 00:00:04,000" in content


class TestWriteTSV:
    """WriteTSV 포맷터 테스트"""

    def test_write_tsv(self, tmp_path):
        """TSV 파일 생성"""
        result = {
            "segments": [
                {"start": 1.5, "end": 3.7, "text": " Hello world"},
                {"start": 3.7, "end": 6.2, "text": " How are you?"},
            ]
        }

        writer = WriteTSV(str(tmp_path))
        output_path = writer(result, "test.mp3", {})

        with open(output_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 헤더 확인
        assert "start\tend\ttext" in lines[0]

        # 데이터 확인 (밀리초 단위)
        assert "1500\t3700\tHello world" in lines[1]
        assert "3700\t6200\tHow are you?" in lines[2]


class TestWriteJSON:
    """WriteJSON 포맷터 테스트"""

    def test_write_json(self, tmp_path):
        """JSON 파일 생성"""
        result = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": " Hello"},
                {"start": 2.0, "end": 4.0, "text": " World"},
            ]
        }

        writer = WriteJSON(str(tmp_path))
        output_path = writer(result, "test.mp3", {})

        with open(output_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        # 원본 결과와 동일한지 확인
        assert loaded == result
        assert len(loaded["segments"]) == 2

    def test_json_preserves_unicode(self, tmp_path):
        """유니코드 문자 보존"""
        result = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": " 안녕하세요"},
                {"start": 2.0, "end": 4.0, "text": " こんにちは"},
            ]
        }

        writer = WriteJSON(str(tmp_path))
        output_path = writer(result, "test.mp3", {})

        with open(output_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["segments"][0]["text"] == " 안녕하세요"
        assert loaded["segments"][1]["text"] == " こんにちは"


class TestGetWriter:
    """get_writer 팩토리 함수 테스트"""

    def test_get_txt_writer(self, tmp_path):
        """TXT 작성기 반환"""
        writer = get_writer("txt", str(tmp_path))
        assert isinstance(writer, WriteTXT)

    def test_get_vtt_writer(self, tmp_path):
        """VTT 작성기 반환"""
        writer = get_writer("vtt", str(tmp_path))
        assert isinstance(writer, WriteVTT)

    def test_get_srt_writer(self, tmp_path):
        """SRT 작성기 반환"""
        writer = get_writer("srt", str(tmp_path))
        assert isinstance(writer, WriteSRT)

    def test_get_tsv_writer(self, tmp_path):
        """TSV 작성기 반환"""
        writer = get_writer("tsv", str(tmp_path))
        assert isinstance(writer, WriteTSV)

    def test_get_json_writer(self, tmp_path):
        """JSON 작성기 반환"""
        writer = get_writer("json", str(tmp_path))
        assert isinstance(writer, WriteJSON)

    def test_get_all_writers(self, tmp_path):
        """all 옵션 - 모든 포맷 동시 생성"""
        result = {
            "segments": [
                {"start": 0.0, "end": 2.0, "text": " Test"},
            ]
        }

        writer = get_writer("all", str(tmp_path))
        output_paths = writer(result, "test.mp3", {})

        # 5개 파일 생성 확인
        assert len(output_paths) == 5

        # 각 포맷별 파일 존재 확인
        assert os.path.exists(tmp_path / "test.txt")
        assert os.path.exists(tmp_path / "test.vtt")
        assert os.path.exists(tmp_path / "test.srt")
        assert os.path.exists(tmp_path / "test.tsv")
        assert os.path.exists(tmp_path / "test.json")


class TestFormatOutputLargeV3:
    """format_output_largev3 함수 테스트"""

    def test_format_faster_whisper_segments(self):
        """FasterWhisper 세그먼트 포맷 변환"""
        # Mock FasterWhisper segment
        class MockSegment:
            def __init__(self, start, end, text):
                self.start = start
                self.end = end
                self.text = text

        segments = [
            MockSegment(0.0, 2.5, " Hello world"),
            MockSegment(2.5, 5.0, " How are you?"),
        ]

        result = format_output_largev3(segments)

        # 결과 구조 확인
        assert "segments" in result
        assert len(result["segments"]) == 2

        # 첫 번째 세그먼트 확인
        assert result["segments"][0]["start"] == 0.0
        assert result["segments"][0]["end"] == 2.5
        assert result["segments"][0]["text"] == " Hello world"

        # 두 번째 세그먼트 확인
        assert result["segments"][1]["start"] == 2.5
        assert result["segments"][1]["end"] == 5.0
        assert result["segments"][1]["text"] == " How are you?"

    def test_format_empty_segments(self):
        """빈 세그먼트 리스트"""
        result = format_output_largev3([])

        assert "segments" in result
        assert len(result["segments"]) == 0
