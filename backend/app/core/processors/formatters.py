"""
전사 결과 포맷터 유틸리티

기존 woa/utils.py의 포맷팅 기능을 재사용
"""
import json
import os
import re
import sys
import zlib
from typing import Callable, Optional, TextIO, Dict, Any

# 시스템 인코딩 처리 (woa/utils.py:127-140)
system_encoding = sys.getdefaultencoding()

if system_encoding != "utf-8":
    def make_safe(string):
        """시스템 기본 인코딩으로 표현 불가능한 문자를 '?'로 치환"""
        return string.encode(system_encoding, errors="replace").decode(system_encoding)
else:
    def make_safe(string):
        """utf-8은 모든 유니코드를 인코딩할 수 있으므로 그대로 반환"""
        return string


def format_timestamp(
    seconds: float, always_include_hours: bool = False, decimal_marker: str = "."
) -> str:
    """
    초를 타임스탬프 문자열로 포맷

    기존 코드: woa/utils.py:169-187

    Args:
        seconds: 초 단위 시간
        always_include_hours: 항상 시간 포함 여부
        decimal_marker: 소수점 구분자

    Returns:
        포맷된 타임스탬프 (예: "00:01:23.456" 또는 "01:23.456")
    """
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)

    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000

    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000

    seconds = milliseconds // 1_000
    milliseconds -= seconds * 1_000

    hours_marker = f"{hours:02d}:" if always_include_hours or hours > 0 else ""
    return (
        f"{hours_marker}{minutes:02d}:{seconds:02d}{decimal_marker}{milliseconds:03d}"
    )


class ResultWriter:
    """
    전사 결과 작성 베이스 클래스

    기존 코드: woa/utils.py:190-207
    """
    extension: str

    def __init__(self, output_dir: str):
        self.output_dir = output_dir

    def __call__(self, result: dict, audio_path: str, options: dict):
        """
        전사 결과를 파일로 저장

        Args:
            result: 전사 결과 딕셔너리
            audio_path: 원본 오디오 파일 경로
            options: 출력 옵션 딕셔너리
        """
        audio_basename = os.path.basename(audio_path)
        audio_basename = os.path.splitext(audio_basename)[0]
        output_path = os.path.join(
            self.output_dir, audio_basename + "." + self.extension
        )

        with open(output_path, "w", encoding="utf-8") as f:
            self.write_result(result, file=f, options=options)

        return output_path

    def write_result(self, result: dict, file: TextIO, options: dict):
        raise NotImplementedError


class WriteTXT(ResultWriter):
    """
    TXT 포맷 작성기

    기존 코드: woa/utils.py:210-215
    """
    extension: str = "txt"

    def write_result(self, result: dict, file: TextIO, options: dict):
        for segment in result["segments"]:
            print(segment["text"].strip(), file=file, flush=True)


class SubtitlesWriter(ResultWriter):
    """
    자막 포맷 작성 베이스 클래스

    기존 코드: woa/utils.py:218-323
    """
    always_include_hours: bool
    decimal_marker: str

    def iterate_result(self, result: dict, options: dict):
        """전사 결과를 자막 형식으로 반복"""
        raw_max_line_width: Optional[int] = options.get("max_line_width")
        max_line_count: Optional[int] = options.get("max_line_count")
        highlight_words: bool = options.get("highlight_words", False)
        max_line_width = 1000 if raw_max_line_width is None else raw_max_line_width
        preserve_segments = max_line_count is None or raw_max_line_width is None

        def iterate_subtitles():
            line_len = 0
            line_count = 1
            subtitle = []
            times = []
            last = result["segments"][0]["start"]

            for segment in result["segments"]:
                # 단어 타임스탬프가 없는 경우 처리
                if "words" not in segment or not segment["words"]:
                    continue

                for i, original_timing in enumerate(segment["words"]):
                    timing = original_timing.copy()
                    long_pause = not preserve_segments
                    if "start" in timing:
                        long_pause = long_pause and timing["start"] - last > 3.0
                    else:
                        long_pause = False
                    has_room = line_len + len(timing["word"]) <= max_line_width
                    seg_break = i == 0 and len(subtitle) > 0 and preserve_segments

                    if line_len > 0 and has_room and not long_pause and not seg_break:
                        line_len += len(timing["word"])
                    else:
                        timing["word"] = timing["word"].strip()
                        if (
                            len(subtitle) > 0
                            and max_line_count is not None
                            and (long_pause or line_count >= max_line_count)
                            or seg_break
                        ):
                            yield subtitle, times
                            subtitle = []
                            times = []
                            line_count = 1
                        elif line_len > 0:
                            line_count += 1
                            timing["word"] = "\n" + timing["word"]
                        line_len = len(timing["word"].strip())

                    subtitle.append(timing)
                    times.append((segment["start"], segment["end"], segment.get("speaker")))
                    if "start" in timing:
                        last = timing["start"]

            if len(subtitle) > 0:
                yield subtitle, times

        # 단어 타임스탬프가 있는 경우
        if result["segments"] and "words" in result["segments"][0]:
            for subtitle, timing_list in iterate_subtitles():
                sstart, ssend, speaker = timing_list[0]
                subtitle_start = self.format_timestamp(sstart)
                subtitle_end = self.format_timestamp(ssend)
                subtitle_text = " ".join([word["word"] for word in subtitle])
                has_timing = any(["start" in word for word in subtitle])

                prefix = ""
                if speaker is not None:
                    prefix = f"[{speaker}]: "

                if highlight_words and has_timing:
                    last = subtitle_start
                    all_words = [timing["word"] for timing in subtitle]
                    for i, this_word in enumerate(subtitle):
                        if "start" in this_word:
                            start = self.format_timestamp(this_word["start"])
                            end = self.format_timestamp(this_word["end"])
                            if last != start:
                                yield last, start, subtitle_text

                            yield start, end, prefix + " ".join(
                                [
                                    re.sub(r"^(\s*)(.*)$", r"\1<u>\2</u>", word)
                                    if j == i
                                    else word
                                    for j, word in enumerate(all_words)
                                ]
                            )
                            last = end
                else:
                    yield subtitle_start, subtitle_end, prefix + subtitle_text
        else:
            # 단어 타임스탬프가 없는 경우
            for segment in result["segments"]:
                segment_start = self.format_timestamp(segment["start"])
                segment_end = self.format_timestamp(segment["end"])
                segment_text = segment["text"].strip().replace("-->", "->")
                if "speaker" in segment:
                    segment_text = f"[{segment['speaker']}]: {segment_text}"
                yield segment_start, segment_end, segment_text

    def format_timestamp(self, seconds: float):
        return format_timestamp(
            seconds=seconds,
            always_include_hours=self.always_include_hours,
            decimal_marker=self.decimal_marker,
        )


class WriteVTT(SubtitlesWriter):
    """
    WebVTT 포맷 작성기

    기존 코드: woa/utils.py:326-334
    """
    extension: str = "vtt"
    always_include_hours: bool = False
    decimal_marker: str = "."

    def write_result(self, result: dict, file: TextIO, options: dict):
        print("WEBVTT\n", file=file)
        for start, end, text in self.iterate_result(result, options):
            print(f"{start} --> {end}\n{text}\n", file=file, flush=True)


class WriteSRT(SubtitlesWriter):
    """
    SRT 포맷 작성기

    기존 코드: woa/utils.py:337-346
    """
    extension: str = "srt"
    always_include_hours: bool = True
    decimal_marker: str = ","

    def write_result(self, result: dict, file: TextIO, options: dict):
        for i, (start, end, text) in enumerate(
            self.iterate_result(result, options), start=1
        ):
            print(f"{i}\n{start} --> {end}\n{text}\n", file=file, flush=True)


class WriteTSV(ResultWriter):
    """
    TSV (Tab-Separated Values) 포맷 작성기

    기존 코드: woa/utils.py:349-366
    """
    extension: str = "tsv"

    def write_result(self, result: dict, file: TextIO, options: dict):
        print("start", "end", "text", sep="\t", file=file)
        for segment in result["segments"]:
            print(round(1000 * segment["start"]), file=file, end="\t")
            print(round(1000 * segment["end"]), file=file, end="\t")
            print(segment["text"].strip().replace("\t", " "), file=file, flush=True)


class WriteJSON(ResultWriter):
    """
    JSON 포맷 작성기

    기존 코드: woa/utils.py:369-373
    """
    extension: str = "json"

    def write_result(self, result: dict, file: TextIO, options: dict):
        json.dump(result, file, ensure_ascii=False, indent=2)


def get_writer(
    output_format: str, output_dir: str
) -> Callable[[dict, str, dict], str]:
    """
    출력 포맷에 맞는 작성기 반환

    기존 코드: woa/utils.py:376-396

    Args:
        output_format: 출력 포맷 (txt, vtt, srt, tsv, json, all)
        output_dir: 출력 디렉토리

    Returns:
        작성기 함수
    """
    writers = {
        "txt": WriteTXT,
        "vtt": WriteVTT,
        "srt": WriteSRT,
        "tsv": WriteTSV,
        "json": WriteJSON,
    }

    if output_format == "all":
        all_writers = [writer(output_dir) for writer in writers.values()]

        def write_all(result: dict, audio_path: str, options: dict):
            output_paths = []
            for writer in all_writers:
                path = writer(result, audio_path, options)
                output_paths.append(path)
            return output_paths

        return write_all

    return writers[output_format](output_dir)


def format_output_largev3(segments) -> Dict[str, Any]:
    """
    FasterWhisper large-v3 세그먼트를 표준 포맷으로 변환

    기존 코드: woa/utils.py:411-425

    Args:
        segments: FasterWhisper 세그먼트 이터레이터

    Returns:
        표준 전사 결과 딕셔너리
    """
    output = {
        'segments': [
            {
                'start': segment.start,
                'end': segment.end,
                'text': segment.text,
            }
            for segment in segments
        ],
    }

    return output
