# 비판적 갭 분석 (Gap Analysis) — MC

> 관련: [02_Feature.md](./02_Feature.md), [03_Business_Rules.md](./03_Business_Rules.md), [04_Screen_Spec.md](./04_Screen_Spec.md), [04_Flow.md](./04_Flow.md)
> 작성: 2026-04-26
> 상태: ✅ **Confirmed — 2026-04-26 V1.0 결정으로 GAP-H-02·M-01·M-02·M-08 닫힘**

> ## 갭 마감 갱신 (2026-04-26)
>
> | GAP-ID | 마감 사유 |
> |--------|--------|
> | **GAP-H-02 V1 스코프 과대** | ✅ **Closed** — V1.0 = 26 FR (4~6개월), V1.1·V1.2 분리. iet03 OQ-05-01 답: "(나) 권장 그대로". |
> | **GAP-M-01 일정 알림 V1 부재** | ✅ **Closed** — FR-NOTIFY-01 / BR-NOTIFY-01 V1 편입. OS 시스템 알림. |
> | **GAP-M-02 일정 충돌 검사 V1 부재** | ✅ **Closed** — FR-CONFLICT-01 / BR-CONFLICT-01 V1 편입. LLM 없이 SQL. |
> | **GAP-M-08 회고 저장 형식 가역성** | ✅ **Closed** — 별도 파일 `YYYY/MM/DD-review.md` (BR-DAY-01 갱신). |
> | GAP-C-01·C-02·C-03 | 변동 없음 — Phase 4 PoC로 해결. |
> | GAP-H-01·H-03·H-04·H-05 | 변동 없음 — Phase 4 설계 중 처리. |
> | GAP-M-03·M-04·M-05·M-06·M-07 | 변동 없음 — V1.x 또는 V2 검토. |

---

## 분류 기준

| 등급 | 의미 |
|------|------|
| 🔴 Critical | 미해결 시 V1 개발/사용 불가 |
| 🟠 High | 사용 후 신뢰 깨짐 또는 데이터 손실 위험 |
| 🟡 Medium | 개선 영역, V1 또는 V1.5에 검토 |
| 💡 Idea | 새 기능 제안, 우선순위 별도 |

---

## 🔴 Critical Gaps (V1 개발 전 해결 필수)

| GAP-ID | 항목 | 내용 | 해결 방향 |
|--------|------|------|---------|
| GAP-C-01 | **LLM 응답 시간 실측 미완료** | Phi-3 mini ONNX on Intel NPU의 한국어 슬롯 추출 속도가 추정값. 1~2초 가정이 5~10초로 나오면 음성 UX 망가짐. | Phase 4 진입 전 PoC: Phi-3 mini INT4 ONNX를 NPU에 올려 한국어 발화 10건 측정. 실패 시 모델 다운(Llama-3.2-1B 등) 검토. |
| GAP-C-02 | **Whisper 한국어 정확도 환경 측정** | 92~96%는 표준 벤치. iet03의 실제 마이크·환경에서는 다를 수 있음. 80% 미만이면 "재발화 빈도 ↑" 으로 신뢰 깨짐. | Phase 4 PoC: Whisper Base/Small 둘 다 받아쓰고 사용자 검수. 결과로 디폴트 모델 결정. |
| GAP-C-03 | **데이터 백업·복구 전략 미정** | 단일 사용자 + 로컬 = 디스크 손상 시 모든 데이터 손실. .md는 OS 동기화 폴더로 백업 가능하나 SQLite 인덱스는? | (a) SQLite 매일 export → MC-Notes 폴더에 저장 (b) MC가 인덱스를 .md에서 재구축 가능하도록 설계. **(b) 권장**. |

---

## 🟠 High Risk Gaps (큰 위험)

| GAP-ID | 항목 | 내용 | 해결 방향 |
|--------|------|------|---------|
| GAP-H-01 | **외부 편집 동시성** | LocalDocsHub viewer + 메모장/VS Code + MC 셋이 같은 .md 만짐. chokidar 디바운스만으로 충분한지 의문. partial write·잠금·체크섬 검증 필요. | Phase 4 ADR: 충돌 감지 알고리즘 (last-modified + 체크섬 비교) + 충돌 시 BR-MEMO-07 적용. 자동 백업 .md.bak. |
| GAP-H-02 | **V1 스코프 = 27 FR** | 1인 개발자 6~10개월 추정. 본업 병행이면 1년+. 의욕 잃기 쉬운 구조. | (Step 5 권고) **MVP 정의 명확화**: 진짜 V1.0 = 표준 21 + Whisper(VOICE) + 임베딩(SEARCH/TAG)만 = **24 FR**. SLOT은 V1.1, UX 혁신은 V1.2~. **iet03 결정 필요**. |
| GAP-H-03 | **모델 메모리 장기 운영** | Whisper+BGE+Phi-3 = ~2.3GB. 시스템 사용 중 free RAM 압박 시 swap. 다음 음성 호출 시 reload 10~20초. | BR-AI-09 적용 + Phase 4 모델 keep-alive 정책 정밀화. 옵션: keep-alive 무한, RAM 8GB 이하 시 자동 unload 등 설정 화면 노출. |
| GAP-H-04 | **AI 모델 ONNX 변환·검증 미완료** | "Phi-3 mini INT4 ONNX on Intel NPU OpenVINO" 경로의 실제 모델 파일·런타임이 검증되지 않음. Hugging Face에 직접 사용 가능한 변환본 있는지 확인 필요. | Phase 4 PoC 첫 작업: Optimum-Intel + IR 변환 → NPU 실행. 안 되면 GPU(SYCL) fallback. |
| GAP-H-05 | **권한 회수 시 사용자 데이터 일관성** | GitHub 토큰 회수 시 캐시 read-only 유지(BR-GIT-06)하지만, 사용자가 캐시 기반으로 잘못된 의사결정할 위험 ("이 이슈 아직 open인 줄") | 캐시 데이터에 "마지막 동기 시각 + 만료 경고" UI 강제 표시. |

---

## 🟡 Medium Gaps (V1 또는 V1.5)

| GAP-ID | 항목 | 내용 | 권장 |
|--------|------|------|-----|
| GAP-M-01 | **일정 알림 채널 V1 부재** | iet03가 메일 알림 V2라고 했지만 OS 시스템 알림 한 줄은 가벼움. V1에 두는 게 자연스러움. (BR-?-02 후보) | **V1에 OS 통지만 포함 권장**. 메일/슬랙은 V2. |
| GAP-M-02 | **일정 충돌 검사 V1 부재** | 사용자가 시나리오 A에서 충돌 검사 묘사했으나 Multi-turn agent가 V2로 미뤄지면서 충돌 검사도 함께 빠짐. | **V1에 단순 충돌 검사 포함**: 일정 등록 시 같은 시간대 일정 있으면 경고만 (LLM 없이 SQL 가능). |
| GAP-M-03 | **모바일 부재** | V1은 Windows 데스크톱만. 외부에서 캡처 필요할 때 메모 도구 분리. | (V2 검토) 가벼운 PWA 또는 웹 진입 — 캡처만 가능한 mini view. |
| GAP-M-04 | **Time Constellation 항목 30개+ 시각 복잡** | 도전적이지만 항목 많을 때 가독성 ↓. | 디폴트 토글 OFF + 사용자가 켤 때만. 30개+ 시 "필터 적용" 권장 표시. |
| GAP-M-05 | **항목 일괄 편집 부재** | 여러 항목 선택 → 태그 일괄 추가/삭제 기능 없음. PROJ-04 사후 묶음과 일부 겹침. | V1.1 검토. |
| GAP-M-06 | **데이터 export·import** | 다른 도구로 이전 가능성 = MC 신뢰의 일부. .md는 이미 호환되지만 메타(태그 매핑)는 별도. | V1에 단순 JSON export 버튼만 포함 권장. |
| GAP-M-07 | **검색 결과 정렬·필터** | 의미 검색 결과를 기간/태그/객체타입으로 좁히는 후속 필터 미정의. | 기본 정렬: 의미 점수. 필터 V1.1. |
| GAP-M-08 | **회고 저장 형식의 가역성** | BR-DAY-01: 오늘 .md `## 회고` 섹션 append. 그러나 사용자가 .md를 외부에서 손대면 회고-원문 분리 어려움. | 회고를 별도 파일(`MC-Notes/.../26-review.md`)로 분리 권장? — **iet03 결정 필요**. |

---

## 💡 Ideas — 제안 (V2~)

| IDEA-ID | 제안 | 근거 |
|---------|-----|------|
| IDEA-01 | **회의 전 자동 컨텍스트 풀(Prep)** — 미팅 5분 전 OS 알림 + 관련 메모/이슈/이전 미팅 메모 자동 모음 | iet03 시나리오의 "스케줄 = 컨텍스트 진입점" 가치 자동화. NPU 임베딩으로 전날 자동 검색. |
| IDEA-02 | **음성 패턴 적응** — 사용자 발음·자주 쓰는 표현 학습해서 Whisper 후처리 사전 자동 보강 | 시간 갈수록 정확도 ↑ |
| IDEA-03 | **일주일 패턴 인사이트** — "당신은 화요일 오후에 가장 생산적입니다" 같은 패턴 표시 (FR-UX-03 ECG의 발전형) | 데이터 누적 후 |
| IDEA-04 | **외부 .ics 캘린더 가져오기** — Google/Outlook iCal 일방향 import (외부 SaaS 저장 안 함, 읽기만) | iet03가 본인 캘린더 다른 곳에 두면 통합 진입 |
| IDEA-05 | **Plug-in 형태 LocalDocsHub 통합** — MC 화면 안에서 LocalDocsHub viewer 임베드 (iframe) — 사이드 패널 전환 없이 .md 보기 | "한 화면 연결성" 강화. LocalDocsHub 코드 수정 X. |
| IDEA-06 | **태스크 시간 추정·실측 비교** — "예상 30분 / 실제 45분" 학습 후 일정 자동 추정 보조 | Phase 6/V2 |
| IDEA-07 | **Voice-only 모드** — 디스플레이 끄고 음성만으로 프리뷰·캡처·회고 (저녁 휴식 시) | 차별화 강 |
| IDEA-08 | **MC 자체의 .md 노트화** — MC 사용 자체가 또 하나의 프로젝트. iet03가 MC 사용 회고 기록 = 도구 개선 피드백 자동 수집 | Meta layer |

---

## 새로 발견한 Open Questions

| OQ-ID | 질문 | 등급 | 기한 |
|-------|------|----|------|
| OQ-05-01 | V1 스코프 — 27 FR 그대로 갈지, MVP(24 FR)로 좁힐지 | High | Step 6 진입 전 |
| OQ-05-02 | 일정 알림 — V1 OS 통지 포함? | Medium | Step 6 |
| OQ-05-03 | 일정 충돌 검사 — V1 단순 SQL 충돌 검사 포함? | Medium | Step 6 |
| OQ-05-04 | 회고를 일자 .md 안에 append vs 별도 파일 분리 | Medium | Step 6 |
| OQ-05-05 | 데이터 백업 — JSON export 디폴트 ON/OFF | Medium | Step 6 |

---

## V1 진입 전 PoC 권장 (Phase 4 Designer가 가장 먼저)

GAP-C-01·02·H-04 해결을 위한 1주 PoC:

1. **Day 1~2**: Phi-3 mini INT4 ONNX 변환 + Intel NPU 로드 — 한국어 발화 10건 슬롯 추출 측정
2. **Day 3**: Whisper Base/Small ONNX 한국어 받아쓰기 정확도 측정 (조용한 환경, 일반 환경)
3. **Day 4**: BGE-small-ko ONNX NPU 임베딩 속도 + 검색 결과 품질 (메모 50개 샘플)
4. **Day 5**: PoC 결과로 V1 모델 디폴트 확정 + GAP-C-01·02 닫기

PoC 실패 시 fallback 단계:
- NPU → iGPU (DirectML)
- iGPU → CPU
- 모델 → 더 작은 변형 (Phi-3.5-mini, Llama-3.2-1B 등)

---

## 다음

→ Step 6 ([06_Summary.md](./06_Summary.md)): BA Readiness Score 계산 + Phase 2 핸드오프.
