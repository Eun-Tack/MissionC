# ADR-003: AI/NPU 추론 파이프라인

> 상태: Accepted | 결정일: 2026-04-27
> 결정자: iet03 (Intel Core Ultra 7 355 NPU 직접 활용)

---

## 컨텍스트

ai-worker는 Windows 로컬 Python 프로세스다 (ADR-001). Intel Core Ultra 7 355에는 NPU(최대 13 TOPS)와 iGPU(Intel Arc Graphics)가 있다. OpenVINO + Optimum-Intel을 통해 ONNX 모델을 NPU EP에서 실행할 수 있다.

V1.0 모델 3종 (Whisper Base ONNX, BGE-small-ko ONNX, silero-VAD), V1.1에 Phi-3 mini INT4 추가.

---

## 결정

**OpenVINO NPU EP + onnxruntime 이중 EP 전략**: 모델별로 최적 EP를 고정하되, 폴백은 CPU.

```
┌─────────────────────────────────────────────────────────────┐
│  ai-worker (Windows Python 프로세스)                         │
│                                                             │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │ STT 파이프라인       │  │ 임베딩 파이프라인             │  │
│  │                     │  │                              │  │
│  │  mic → silero-VAD   │  │  text →                      │  │
│  │  → audio chunk      │  │  BGE-small-ko ONNX           │  │
│  │  → Whisper Base     │  │  → NPU EP (openvino)         │  │
│  │    ONNX NPU EP      │  │  → 384-dim vector            │  │
│  │  → transcript str   │  │  → sqlite-vec INSERT         │  │
│  │                     │  │                              │  │
│  └─────────────────────┘  └──────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 슬롯 추출 파이프라인 (V1.1)                            │   │
│  │  text → Phi-3 mini INT4 → OpenVINO INT4 NPU EP        │   │
│  │  → JSON slots (title/date/tags/project)               │   │
│  │  폴백: text → 정규식 슬롯 추출 (Phi-3 실패 시)          │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  FastAPI 서버 (port 8001)                                    │
│  POST /infer/stt    POST /infer/embed    POST /infer/slot   │
└─────────────────────────────────────────────────────────────┘
```

---

## 모델별 EP 할당

| 모델 | ONNX EP | 폴백 EP | 메모리 | 지연 목표 |
|------|---------|--------|--------|---------|
| silero-VAD | CPU (경량, 1MB) | — | ~20MB | ≤ 5ms/chunk |
| Whisper Base ONNX | NPU (OpenVINO) | CPU | ~150MB | ≤ 3s / 10s 음성 |
| BGE-small-ko ONNX | NPU (OpenVINO) | CPU | ~130MB | ≤ 200ms / 문장 |
| Phi-3 mini INT4 (V1.1) | NPU (OpenVINO) | CPU | ~2.4GB | ≤ 5s / 슬롯 추출 |

**NPU 동시 실행 제약**: OpenVINO NPU EP는 동시 2개 모델 추론 지원 (드라이버 v1.5+). STT와 임베딩은 순차 실행. Phi-3는 V1.1이므로 V1.0 NPU 경합 없음.

---

## 구현 세부

### ai-worker 서버 (FastAPI)

```python
# ai_worker/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
import onnxruntime as ort

models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # OpenVINO EP 우선, 실패 시 CPU 폴백
    providers = [("OpenVINOExecutionProvider", {"device_type": "NPU"}), "CPUExecutionProvider"]
    models["whisper"] = ort.InferenceSession("models/whisper-base.onnx", providers=providers)
    models["bge"] = ort.InferenceSession("models/bge-small-ko.onnx", providers=providers)
    yield
    models.clear()

app = FastAPI(lifespan=lifespan)

@app.post("/infer/embed")
async def embed(text: str) -> list[float]:
    # BGE-small-ko: tokenize → NPU 추론 → 384-dim vector
    ...
```

### 모델 다운로드 & 변환

```
# 최초 설정 (once)
python tools/setup_models.py
  → HuggingFace에서 ONNX 모델 다운로드
  → OpenVINO IR 변환 (INT8/INT4)
  → models/ 폴더에 저장 (git-ignored)
```

### 모델 파일 위치

```
schedule/
  models/
    whisper-base.onnx          # ~150MB
    whisper-base-openvino/     # OpenVINO IR
    bge-small-ko.onnx          # ~130MB
    bge-small-ko-openvino/
    silero_vad.onnx            # ~1MB
    phi3-mini-int4-openvino/   # ~2.4GB, V1.1
```

---

## 신뢰도 & 에러 처리

### Whisper 신뢰도 (OQ-BA-01 해결)

| confidence | 처리 |
|-----------|------|
| ≥ 0.8 | 자동 수락 |
| 0.6 ~ 0.8 | 노란 밑줄 + "확인 필요" 뱃지 표시, 사용자 확인 |
| < 0.6 | 빨간 밑줄 + "재시도" 버튼 (BR-AI-06) |

초기값 0.6은 OQ-BA-01로 Phase 4 구현 시 A/B 테스트로 조정 예정.

### NPU EP 폴백

```python
def get_providers(model_name: str) -> list:
    try:
        test = ort.InferenceSession("models/test.onnx",
            providers=[("OpenVINOExecutionProvider", {"device_type": "NPU"})])
        return [("OpenVINOExecutionProvider", {"device_type": "NPU"}), "CPUExecutionProvider"]
    except Exception:
        logger.warning(f"{model_name}: NPU EP unavailable, falling back to CPU")
        return ["CPUExecutionProvider"]
```

---

## core-api → ai-worker 통신

```
POST http://localhost:8001/infer/embed
Content-Type: application/json
{"text": "프로젝트 회의 메모"}

→ 200 OK
{"vector": [0.023, -0.145, ...], "model": "bge-small-ko", "ep": "NPU"}
```

타임아웃: 임베딩 500ms, STT 10s. 초과 시 core-api는 HTTP 503 반환, UI에 "AI 서비스 준비 중" 토스트.

---

## 고려한 대안

| 옵션 | 이유로 제외 |
|------|-----------|
| faster-whisper (CTranslate2) | NPU 미지원, CPU/CUDA만. OpenVINO ONNX가 NPU 직접 접근. |
| llama.cpp (Phi-3) | NPU 미지원. OpenVINO Phi-3 INT4가 더 효율적. |
| 외부 API (OpenAI Whisper) | BR-AUTH-03a 위반 — AI SaaS 외부 송신 금지. |
| DirectML EP | OpenVINO보다 NPU 최적화 낮음. Intel 공식 권장 = OpenVINO. |

---

## 결과

- **V1.0**: silero-VAD(CPU) + Whisper(NPU) + BGE-small-ko(NPU)
- **V1.1**: + Phi-3 mini INT4(NPU)
- NPU 드라이버 업그레이드 시 ai-worker 단독 교체 (ADR-001 근거)
- 모든 추론 로컬 완결 — 외부 AI SaaS 제로 (BR-AUTH-03a)
