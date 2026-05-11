# TS-02: ai-worker 기술 명세

> 서비스: ai-worker | Windows 로컬 Python 프로세스 | 포트 8001
> ADR-001, ADR-003 참조

---

## 책임 범위

- Whisper Base ONNX STT (NPU EP)
- BGE-small-ko 임베딩 (NPU EP)
- silero-VAD 음성 활동 감지 (CPU)
- Phi-3 mini INT4 슬롯 추출 (V1.1, NPU EP)
- FastAPI HTTP 서버 (core-api의 인터페이스)

---

## API 명세

```
POST /infer/embed
Body: {"text": "string"}
Response: {"vector": float[384], "ep": "NPU"|"CPU", "latency_ms": int}

POST /infer/stt
Body: multipart/form-data — audio: WAV bytes
Response: {"transcript": "string", "confidence": float, "latency_ms": int}

POST /infer/slot   (V1.1)
Body: {"text": "string"}
Response: {"slots": {"title": str, "date": str|null, "tags": list, "project": str|null}}

GET /health
Response: {"status": "ok", "ep": "NPU"|"CPU", "models_loaded": list}
```

---

## 모델 로딩 순서

```python
MODELS_DIR = Path("models")

async def load_models():
    providers = detect_providers()  # NPU 가용 여부 체크
    models["vad"]    = ort.InferenceSession(MODELS_DIR / "silero_vad.onnx",
                           providers=["CPUExecutionProvider"])
    models["whisper"] = ort.InferenceSession(MODELS_DIR / "whisper-base-openvino" / "model.onnx",
                           providers=providers)
    models["bge"]    = ort.InferenceSession(MODELS_DIR / "bge-small-ko-openvino" / "model.onnx",
                           providers=providers)
```

---

## STT 파이프라인 상세

```
마이크 입력
  → PyAudio 스트림 (16kHz, mono, int16)
  → silero-VAD 청크 단위 분석 (30ms)
  → VAD silence 2초 감지 → 세그먼트 종료
  → WAV bytes → Whisper Base ONNX 추론
  → transcript + confidence
  → confidence < 0.6: 재시도 트리거 (BR-AI-06)
```

---

## 임베딩 배치 처리

단건 요청은 즉시 처리 (≤200ms 목표).
대량 인덱싱(초기 import)은 배치 큐:
```python
BATCH_SIZE = 32
FLUSH_INTERVAL = 5.0  # seconds
```

---

## Windows 서비스 등록 (Task Scheduler)

```xml
<!-- ai_worker/install_task.xml -->
<Task>
  <Triggers><BootTrigger/></Triggers>
  <Actions>
    <Exec>
      <Command>python</Command>
      <Arguments>C:\...\schedule\ai_worker\main.py</Arguments>
    </Exec>
  </Actions>
</Task>
```

설치: `schtasks /create /xml install_task.xml /tn "MC-AIWorker"`
