# World-of-ASR 코드베이스 개선 보고서

## 📋 개요
이 보고서는 World-of-ASR 프로젝트의 코드 품질, 아키텍처, 보안, 유지보수성 측면에서 발견된 개선점들을 정리한 문서입니다.

---

## 🔴 심각도 높음 (Critical)

### 1. **예외 처리 누락 및 불충분**

**위치:**
- `sock_streaming_client.py:48-49`, `63-64`
- `streaming_audio_save.py:60-65`
- `multi_triton_streaming.py:103`

**문제점:**
```python
except:
    pass
```
- bare except 문을 사용하여 모든 예외를 무시
- 디버깅이 불가능하고 에러 추적이 어려움
- KeyboardInterrupt, SystemExit 등 시스템 예외까지 잡아버림

**영향:**
- 네트워크 오류, 오디오 스트림 오류가 조용히 무시됨
- 사용자는 왜 동작이 멈췄는지 알 수 없음
- 프로덕션 환경에서 치명적인 버그 원인

**권장사항:**
- 구체적인 예외 타입 지정 (Exception, ConnectionError 등)
- 로깅 추가
- 사용자에게 적절한 피드백 제공

---

### 2. **전역 변수 사용 및 스레드 안전성 문제**

**위치:**
- `sock_streaming_client.py:29-30`, `37-39`, `67-68`, `71-73`, `80-81`

**문제점:**
```python
p = pyaudio.PyAudio()
streaming = False
p = pyaudio.PyAudio()  # 중복 선언
stop_event = threading.Event()

def start_audio():
    global s  # 전역 소켓
    global send_thread, recv_thread  # 전역 스레드
```

**영향:**
- 동시에 여러 연결을 처리할 수 없음
- 스레드 간 경쟁 조건(race condition) 발생 가능
- 재사용성이 떨어지고 테스트가 어려움
- `s` 소켓 변수가 전역으로 선언되지 않아 NameError 발생 가능

**권장사항:**
- 클래스 기반 구조로 리팩토링
- 상태를 객체 내부에 캡슐화
- Lock/RLock을 사용한 스레드 안전성 보장

---

### 3. **하드코딩된 설정값**

**위치:**
- `multi_triton_streaming.py:22`
- `sock_streaming_client.py:32-33`
- `app.py:460`

**문제점:**
```python
url = "10.17.23.228:8123"  # 하드코딩된 IP
HOST = "127.0.0.1"
PORT = 43007
port=16389
```

**영향:**
- 환경별 배포가 어려움
- 보안 취약점 (내부 IP 노출)
- 설정 변경시 코드 수정 필요

**권장사항:**
- 환경 변수 또는 설정 파일 사용
- `.env.example` 파일 제공
- 민감한 정보는 별도 관리

---

### 4. **리소스 누수 위험**

**위치:**
- `sock_streaming_client.py:42-52`, `111-149`
- `streaming_audio_save.py:58`
- `woa/events.py:48-64`, `136-145`

**문제점:**
```python
stream = p.open(...)  # try 블록 외부에서 열림
try:
    while not stop_event.is_set():
        ...
except:
    pass  # 예외 발생시 stream이 닫히지 않을 수 있음
finally:
    stream.stop_stream()
    stream.close()

# app.py의 초기화 코드
s = socket.socket(...)
s.connect(...)
# finally 없이 s.close() 호출
```

**영향:**
- 오디오 스트림이 닫히지 않아 장치가 잠김
- 소켓 연결이 정리되지 않아 포트 고갈
- 메모리 누수 가능성

**권장사항:**
- Context manager (with 문) 사용
- 모든 리소스에 대해 finally 또는 with 보장
- 명시적인 cleanup 메서드 구현

---

## 🟠 심각도 중간 (High)

### 5. **코드 중복**

**위치:**
- `app.py`: 3개 탭(Whisper, FasterWhisper, Fastconformer)에서 거의 동일한 UI 코드 반복
- `app.py:46-51`, `133-139`, `246-251` - 동일한 함수 3번 정의

**문제점:**
```python
def change_interactive2(min, max, val):  # 3번 정의됨
    return [
        gr.Number.update(visible=val),
        gr.Number.update(visible=val),
    ]
```

**영향:**
- 유지보수 비용 증가
- 버그 수정시 여러 곳 수정 필요
- 일관성 유지 어려움

**권장사항:**
- UI 컴포넌트를 함수로 추출
- 공통 로직을 유틸리티 함수로 분리
- 설정을 데이터 구조로 관리

---

### 6. **타입 힌트 부족**

**위치:**
- 대부분의 함수에서 타입 힌트 없음
- `woa/events.py`, `sock_streaming_client.py`, `multi_triton_streaming.py`

**문제점:**
```python
def send_audio():  # 매개변수와 반환값 타입 없음
def receiver(conn):  # conn이 무엇인지 불명확
def diarization_process(filename, results, token, min_speakers=2, max_speakers=15):
```

**영향:**
- IDE의 자동완성 지원 부족
- 타입 관련 버그 발견 어려움
- 코드 가독성 저하
- 리팩토링 시 실수 가능성 증가

**권장사항:**
- Python 3.11+의 타입 힌트 적극 활용
- mypy 등 정적 타입 체커 도입
- typing 모듈 활용 (Optional, List, Dict 등)

---

### 7. **불명확한 변수명 및 주석**

**위치:**
- `sock_streaming_client.py:27` - "스테레오"라고 주석되어 있으나 실제로는 `CHANNELS = 1` (모노)
- `woa/diarize.py:316` - `self.threshold` 정의되지 않음
- `app.py:159`, `272` - `min_value` 대신 `minimum` 사용해야 함

**문제점:**
```python
CHANNELS = 1  # 스테레오  <- 잘못된 주석
batch_size = gr.Slider(label="Batch Size", min_value=1, ...)  # 잘못된 속성명
```

**영향:**
- 코드 이해도 저하
- 잘못된 정보로 버그 유발
- 런타임 에러 발생 가능

**권장사항:**
- 주석과 코드의 일치성 검증
- 의미있는 변수명 사용
- Gradio API 문서에 맞는 올바른 파라미터명 사용

---

### 8. **테스트 코드 부재**

**위치:**
- `sock_streaming_client_unittest.py`는 이름과 달리 유닛 테스트가 아님 (단순히 복사본)

**문제점:**
- 실제 테스트 코드가 존재하지 않음
- 리팩토링 시 회귀 테스트 불가능
- CI/CD 파이프라인 구축 어려움

**영향:**
- 코드 변경시 기존 기능 동작 보장 어려움
- 버그 재발 방지 메커니즘 없음

**권장사항:**
- pytest 프레임워크 도입
- 핵심 로직에 대한 단위 테스트 작성
- 통합 테스트 추가
- CI에서 자동 테스트 실행

---

## 🟡 심각도 낮음 (Medium)

### 9. **의존성 관리 문제**

**위치:**
- `requirements.txt`
- `requirements-streaming.txt`

**문제점:**
- 버전이 명시되지 않은 패키지들 (`whisper-timestamped`, `librosa` 등)
- `docker==6.1.3` - 매우 구체적인 버전 고정
- `gradio==3.45.1` - 구버전 (최신 5.x 버전 사용 가능)

**영향:**
- 재현 가능한 환경 구축 어려움
- 의존성 충돌 가능성
- 보안 패치 누락 위험

**권장사항:**
- 모든 의존성에 버전 범위 명시 (`>=`, `<` 사용)
- `pip-tools`나 `poetry` 사용 고려
- 정기적인 의존성 업데이트
- `requirements-dev.txt` 분리

---

### 10. **문서화 부족**

**위치:**
- `README.md`
- 모든 Python 모듈

**문제점:**
```markdown
# README.md - 설치 방법만 있음
# 아키텍처 설명 없음
# API 문서 없음
# 예제 부족
```

**영향:**
- 신규 개발자 온보딩 어려움
- 기능 파악 시간 소요
- 유지보수 어려움

**권장사항:**
- docstring 추가 (Google/NumPy 스타일)
- 아키텍처 다이어그램 추가
- 사용 예제 확충
- API 레퍼런스 문서 작성

---

### 11. **비효율적인 파일 경로 처리**

**위치:**
- `app.py:9-10`, `77-78`, `157-160`, `337-340`, `356-358`
- `woa/events.py:76-80`, `157-160`, `247-251`

**문제점:**
```python
os.getcwd() + "/output/"  # 문자열 연결
os.mkdir(os.getcwd() + "/output/" + filename_alpha_numeric)
```

**영향:**
- Windows에서 경로 구분자 문제 발생 가능
- 코드 가독성 저하
- 경로 조작 취약점 가능성

**권장사항:**
- `pathlib.Path` 사용
- `os.path.join()` 사용
- 기본 출력 디렉토리를 상수로 정의

---

### 12. **설정과 로직의 혼재**

**위치:**
- `app.py:460-464`
- `woa/events.py:11-14`

**문제점:**
```python
port=16389  # 하드코딩
if os.environ.get("IP_ADDR") is not None:
    ui.queue(concurrency_count=10).launch(...)
else:
    ui.queue(concurrency_count=10).launch(server_port=port)
```

**영향:**
- 설정 변경이 코드 변경 필요
- 테스트 환경과 운영 환경 분리 어려움

**권장사항:**
- 설정을 별도 파일로 분리 (config.py, .env)
- 환경별 설정 파일 지원
- pydantic 등 설정 검증 라이브러리 활용

---

### 13. **불필요한 import 및 코드**

**위치:**
- `app.py:1-2` - `gc`, `tqdm` import했으나 직접 사용하지 않음 (이벤트 핸들러에서만 사용)
- `sock_streaming_client.py:29-30`, `37` - `pyaudio.PyAudio()` 중복 인스턴스 생성
- `sock_streaming_client.py:30` - `streaming` 변수 선언했으나 사용하지 않음

**문제점:**
```python
import gc  # 사용되지 않음
import tqdm  # 사용되지 않음
p = pyaudio.PyAudio()
streaming = False  # 사용되지 않음
p = pyaudio.PyAudio()  # 중복
```

**영향:**
- 코드 이해도 저하
- 메모리 낭비 (중복 인스턴스)

**권장사항:**
- 사용하지 않는 import 제거 (flake8, ruff 활용)
- 중복 코드 제거
- 사용하지 않는 변수 제거

---

### 14. **에러 메시지 및 로깅 부족**

**위치:**
- 전반적으로 로깅이 거의 없음
- `sock_streaming_client.py:92` - print만 사용
- `multi_triton_streaming.py:43` - print만 사용

**문제점:**
```python
print(f"[LOG]Error during shutdown: {e}")  # 파일에 기록되지 않음
print(transcripts)  # 디버그용 print
```

**영향:**
- 프로덕션 환경에서 문제 추적 어려움
- 로그 레벨 조정 불가능
- 로그 파일 저장 불가능

**권장사항:**
- logging 모듈 사용
- 로그 레벨 구분 (DEBUG, INFO, WARNING, ERROR)
- 로그 파일 저장 설정
- 구조화된 로깅 (JSON 포맷 등)

---

## 🟢 개선 제안 (Nice to Have)

### 15. **성능 최적화 기회**

**위치:**
- `woa/diarize.py:389-401` - 반복문에서 모델 추론

**문제점:**
```python
for transcript in result[0]["segments"]:
    # 세그먼트마다 개별 추론
    embedding = embedding_model(audio_segment)
    embeddings.append(embedding.detach().numpy())
```

**개선 제안:**
- 배치 처리로 여러 세그먼트를 한번에 처리
- GPU 활용도 향상

---

### 16. **UI/UX 개선**

**위치:**
- `app.py` - Gradio UI

**문제점:**
- 진행 상태 피드백 부족
- 에러 발생시 사용자 친화적 메시지 없음
- 파일 업로드 크기 제한 없음

**개선 제안:**
- Progress bar 상세화
- 친절한 에러 메시지
- 파일 크기/형식 검증
- 결과 미리보기 기능

---

### 17. **Docker 관련 개선**

**위치:**
- `woa/events.py:220-236` - Docker 컨테이너 직접 조작

**문제점:**
```python
container = client.containers.get(CONTAINER_ID)
result = container.exec_run(f"python run_nemo.py {audio}", stderr=False)
```

**개선 제안:**
- Docker API 에러 처리 추가
- 컨테이너 상태 확인
- 타임아웃 설정
- REST API 또는 gRPC 사용 고려

---

### 18. **보안 강화**

**위치:**
- 전체 코드베이스

**문제점:**
- 입력 검증 부족
- 경로 탐색(Path Traversal) 취약점 가능성
- HF_TOKEN 등 민감 정보 처리

**개선 제안:**
- 사용자 입력 검증 및 sanitization
- 파일 경로 정규화 및 검증
- 시크릿 관리 도구 사용 (AWS Secrets Manager, Vault 등)
- HTTPS/TLS 적용 고려

---

### 19. **모니터링 및 메트릭**

**현재 상태:**
- 성능 측정 없음
- 리소스 사용량 추적 없음

**개선 제안:**
- Prometheus + Grafana 통합
- 처리 시간, 메모리 사용량 추적
- 에러율 모니터링
- Health check 엔드포인트 추가

---

### 20. **코드 스타일 및 린팅**

**현재 상태:**
- 일관되지 않은 코드 스타일
- 린터 설정 파일 없음

**개선 제안:**
- Black (코드 포매터) 적용
- Ruff 또는 flake8 (린터) 설정
- isort (import 정렬)
- pre-commit hooks 설정
- `.editorconfig` 추가

---

## 📊 우선순위 로드맵

### Phase 1 (긴급) - 1-2주
1. 예외 처리 개선
2. 전역 변수를 클래스 기반 구조로 리팩토링
3. 리소스 누수 방지 (context manager 적용)
4. 하드코딩된 설정을 환경 변수로 분리

### Phase 2 (중요) - 2-4주
5. 타입 힌트 추가
6. 테스트 코드 작성
7. 로깅 시스템 구축
8. 코드 중복 제거

### Phase 3 (개선) - 1-2개월
9. 의존성 관리 개선
10. 문서화 강화
11. pathlib 적용
12. 보안 강화

### Phase 4 (최적화) - 지속적
13. 성능 최적화
14. 모니터링 구축
15. CI/CD 파이프라인 구축

---

## 🎯 결론

이 코드베이스는 기본적인 ASR 기능은 동작하지만, **프로덕션 환경에서 사용하기에는 여러 문제점**이 있습니다. 특히:

- ✅ **긍정적 측면**: Gradio를 활용한 사용자 친화적 UI, 다양한 ASR 모델 지원
- ⚠️ **개선 필요**: 에러 처리, 리소스 관리, 테스트, 문서화

**가장 먼저 개선해야 할 3가지:**
1. 예외 처리 및 로깅
2. 전역 변수 제거 및 구조 개선
3. 리소스 관리 (context manager)

이러한 개선을 통해 안정성, 유지보수성, 확장성을 크게 향상시킬 수 있습니다.
