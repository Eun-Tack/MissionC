# ADR-009: 하드웨어 역량 감지 및 기능 활성화

> 날짜: 2026-05-04 | 상태: Accepted
> 결정자: iet03 | 맥락: Phase 4 v1.3 — NPU/GPU 없는 사용자 지원

---

## 배경

다른 사용자가 설치할 때 NPU(Intel Core Ultra) 또는 GPU(DirectML/CUDA)가 없을 수 있다. NPU/GPU 없이 STT·의미검색을 CPU에서 실행하면 응답 속도가 크게 저하된다. 사용자 경험을 위해 이 기능들을 **조건부 비활성화**하고, 어떤 기능이 활성인지 명확히 안내한다.

---

## 결정

### 감지 순서 및 결과

```python
# ai_worker/capability.py
def detect_capability() -> str:
    import onnxruntime as ort
    providers = ort.get_available_providers()
    if "QNNExecutionProvider" in providers:
        return "NPU"
    if "DmlExecutionProvider" in providers:
        return "GPU_DML"
    if "CUDAExecutionProvider" in providers:
        return "GPU_CUDA"
    return "CPU_ONLY"
```

결과를 `settings.ai_capability_level`에 저장.

### 기능 활성화 매트릭스

| 기능 | NPU | GPU (DML/CUDA) | CPU only |
|------|-----|----------------|---------|
| 의미 검색 (임베딩) | ✅ ≤200ms | ✅ ~300ms | ❌ 비활성 |
| STT Voice Capture | ✅ ≤3s | ✅ ~5s | ❌ 비활성 |
| 태그 자동 제안 | ✅ 즉시 | ✅ 즉시 | ❌ 비활성 |
| Phi-3 슬롯 추출 (V1.1) | ✅ | ✅ | ❌ 비활성 |
| FTS5 텍스트 검색 | ✅ | ✅ | ✅ 항상 |
| 모든 UI 기능 | ✅ | ✅ | ✅ 항상 |
| 캘린더·조직·프로젝트 뷰 | ✅ | ✅ | ✅ 항상 |

CPU only 시 의미검색 비활성 이유: KoE5 384dim 임베딩을 CPU로 실행하면 쿼리당 ~800ms~2s로 허용 불가.

### 비활성 UI 처리

```
CPU only 상태에서:
- Quick Capture: Voice 버튼 → 회색 + 툴팁 "NPU/GPU 필요"
- 검색창: 텍스트 검색만 동작, "의미 검색 비활성" 배지 표시
- SC-10 Diagnostics: AI 기능 섹션에 "CPU 전용 모드" 안내
```

### 감지 시점

1. **최초 설치 후 첫 실행**: ai-worker 시작 시 자동 감지 → `settings` 저장
2. **매 재시작 시**: 감지 결과 캐시 사용 (재감지 안 함)
3. **수동 재감지**: SC-10 Diagnostics > "하드웨어 재스캔" 버튼

### 모델 다운로드 정책

```python
# 설치 직후 첫 실행 흐름
capability = detect_capability()
if capability == "CPU_ONLY":
    settings.set("ai_capability_level", "CPU_ONLY")
    # 모델 다운로드 건너뜀 → ai-worker 미시작
else:
    download_models_if_missing()   # whisper-base, KoE5
    start_ai_worker()
```

---

## 대안 검토

| 대안 | 거절 이유 |
|------|---------|
| CPU에서 모든 기능 유지 (느리게) | UX 저하 심각. 의미검색 2s+는 허용 불가 |
| Whisper Tiny로 CPU 지원 | 한국어 정확도 급하락. iet03 요청대로 비활성 처리 |
| 클라우드 API fallback | 로컬 원칙 위반 |

---

## Change Log

| 날짜 | 변경 |
|------|------|
| 2026-05-04 | 최초 작성 |
