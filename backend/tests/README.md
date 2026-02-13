# Phase 2 테스트 가이드

## 개요

Phase 2 ASR 모델 통합을 위한 테스트 스위트입니다.

## 테스트 구조

```
tests/
├── conftest.py                    # 공통 fixture 및 설정
├── unit/                          # 단위 테스트
│   ├── test_basic.py             # 환경 검증 테스트 ✅
│   ├── test_formatters.py        # 포맷터 단위 테스트 ✅ (21 tests)
│   └── test_model_manager.py     # ModelManager 테스트 (torch 필요)
└── integration/                   # 통합 테스트
    └── test_model_integration.py # 모델 통합 테스트 (torch 필요)
```

## 테스트 실행

### 의존성 없이 실행 가능한 테스트

```bash
# formatters 테스트 (의존성 없음)
python -m pytest tests/unit/test_formatters.py -v --no-cov

# 기본 환경 테스트
python -m pytest tests/unit/test_basic.py -v --no-cov
```

**결과:**
- ✅ test_formatters.py: 21개 테스트 모두 통과
- ✅ test_basic.py: 5개 테스트 모두 통과

### 전체 의존성 필요한 테스트

다음 테스트들은 torch, faster-whisper 등 전체 의존성 설치가 필요합니다:

```bash
# ModelManager 테스트 (torch, faster-whisper, whisper-timestamped 필요)
python -m pytest tests/unit/test_model_manager.py -v

# 통합 테스트 (모든 의존성 필요)
python -m pytest tests/integration/ -v
```

## 의존성 설치

전체 테스트를 실행하려면:

```bash
# backend 디렉토리에서
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## 테스트 커버리지

### 단위 테스트

#### ✅ test_formatters.py (21 tests)
- `format_timestamp`: 타임스탬프 포맷팅 (6 tests)
- `WriteTXT`: TXT 포맷 작성 (1 test)
- `WriteVTT`: WebVTT 포맷 작성 (2 tests)
- `WriteSRT`: SRT 포맷 작성 (1 test)
- `WriteTSV`: TSV 포맷 작성 (1 test)
- `WriteJSON`: JSON 포맷 작성 (2 tests)
- `get_writer`: 포맷터 팩토리 (6 tests)
- `format_output_largev3`: FasterWhisper 결과 변환 (2 tests)

#### test_model_manager.py (12 tests) - torch 필요
- 싱글톤 패턴 검증
- 모델 캐싱 동작
- 스레드 안전성
- 캐시 정리
- 에러 처리

### 통합 테스트

#### test_model_integration.py - 전체 의존성 필요
- 전사 파이프라인 E2E 테스트
- 스피커 분별 통합 테스트
- 여러 포맷 동시 저장
- 모델 전환 테스트
- 에러 처리 테스트
- 메모리 관리 테스트

## 테스트 작성 가이드

### Fixture 사용

```python
def test_with_sample_data(sample_transcription_result):
    # conftest.py의 fixture 사용
    assert "segments" in sample_transcription_result
```

### Mock 사용

```python
@patch('app.core.models.manager.FasterWhisperModel')
def test_with_mock(mock_model_class):
    mock_instance = Mock()
    mock_model_class.return_value = mock_instance
    # 테스트 로직
```

## CI/CD 통합

### GitHub Actions 예시

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test-formatters:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install minimal dependencies
        run: |
          pip install pytest pytest-cov
      - name: Run formatter tests
        run: |
          python -m pytest tests/unit/test_formatters.py -v --no-cov

  test-full:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install all dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run all tests
        run: |
          python -m pytest tests/ -v
```

## 테스트 결과 요약

### 현재 상태 (2024-02-13)

| 테스트 파일 | 테스트 수 | 상태 | 의존성 |
|------------|---------|------|--------|
| test_basic.py | 5 | ✅ 통과 | 없음 |
| test_formatters.py | 21 | ✅ 통과 | 없음 |
| test_model_manager.py | 12 | ⏳ 대기 | torch, faster-whisper |
| test_model_integration.py | 8 | ⏳ 대기 | torch, 전체 |

**총계:** 26개 테스트 통과, 20개 테스트 의존성 대기

## 다음 단계

1. ✅ Formatters 테스트 작성 완료
2. ✅ ModelManager 테스트 작성 완료
3. ✅ 통합 테스트 작성 완료
4. ⏳ 전체 의존성 설치 후 테스트 실행
5. ⏳ CI/CD 파이프라인 설정
6. ⏳ 테스트 커버리지 70% 목표 달성
