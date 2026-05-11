# Design Summary — MC (Mission Control)

> 문서 ID: DS-MC-1.1
> 작성: 2026-04-27 v1.0 → 2026-05-04 v1.1 개정
> 상태: **Draft v1.1 — 코덱스 외부 검토 반영 완료, iet03 검토 대기**
> 인풋: Phase 3 BA 산출물 11종 + ADR-001~007 + 코덱스 검토 (2026-04-28)

---

## 0. 개정 요약 (v1.0 → v1.1)

코덱스 외부 검토에서 다음 결함 지적을 수용하여 Phase 4 산출물을 보강했다.

| 결함 | v1.0 상태 | v1.1 조치 |
|------|---------|---------|
| `.env`에 토큰 저장 (CLAUDE.md/BR-AUTH 위반) | 명시됨 | **ADR-005** + secret-bridge 도입, Environment_Spec 갱신 |
| 백그라운드 실행 책임 모호 (FR-NOTIFY-01 보장 불가) | 미정 | **ADR-006** 4-tier 모델 + notifier-daemon 분리 |
| http.server → FastAPI 결정 로그 부재 | 미정 | **ADR-007** 결정 로그 작성 |
| `item_github_links` junction 누락 | 누락 | mc_schema.sql에 추가 |
| Capture Inbox 미명세 (TG/voice/quick 통합 큐) | 누락 | `capture_inbox` 테이블 + **SC-09** + FR-INBOX-01 |
| Retry Queue / Notification Center 미명세 | 누락 | `retry_queue`, `notification_events` + **SC-11** + FR-NOTIFY-CTR-01 |
| Diagnostics / Worker 상태판 미명세 | 누락 | **SC-10** + FR-DIAG-01 |
| Credential 컴포넌트 (SC-08 보강) 미명세 | 누락 | **SC-08-Cred** + FR-SET-CRED-01 |
| 검색 결과 화면 (SC-02) 미명세 | 누락 | Screen Spec Addendum SC-02 보강 |
| 파일 충돌 병합 UI (FR-CONFLICT-01) 미명세 | 누락 | **SC-12** + BR-CONFLICT-02~04 |
| `review_memos`, `file_index` 미명세 | 누락 | mc_schema.sql에 추가 |
| 임베딩 차원 (BGE 512 vs 384) 충돌 | 충돌 | KoE5 384 기본 + bge-m3 1024 마이그레이션 옵션 명시 |
| item type 명칭 충돌 (schedule/event, memo/note) | 충돌 | items.type = `schedule` / `task` / `memo` / `project_ref` 4종 통일 |
| 프로젝트 강등 (`is_project` 컬럼) 모호 | 충돌 | `projects.status='paused'` 단일 모델로 확정 |
| BA-Tech 추적성 표 부재 (D1-02 미달) | 누락 | **Traceability_Matrix.md** 작성 (V1.0 30 FR × 6열 100%) |
| OQ-BA-03 TG polling/webhook 결정 | 미정 | TS-03에서 polling 확정 |

### 거절·보류 항목 (코덱스 의견 중 비수용)

| 코덱스 제안 | 처분 | 사유 |
|-----------|------|------|
| Project Hub UI 재설계 명세 (Hero/Orbit/Accelerator Deck 제거) | 명시만 (별도 명세 없음) | CLAUDE.md에 "project_hub.py는 참고만"이 이미 명시. 새 Screen Spec 불필요. |
| Import / Migration 컴포넌트 | V1.1로 연기 | LocalDocsHub 흡수 안 함 정책. 기존 .md 등록은 V1.1 모듈로 분리. |
| `audit_events` 보안 운영 로그 테이블 | V2로 연기 | 1인 로컬 도구에 과잉. notification_events로 V1.0 충분. |
| `model_status` 별도 테이블 | settings 키-값으로 대체 | `worker_status_*` 시드 추가로 충분. |

---

## 1. 설계 산출물 (v1.3 최종)

| 카테고리 | 파일 | 상태 |
|---------|-----|------|
| ADR | [ADR-001 하이브리드 컨테이너](ADR/ADR-001_Hybrid_Container_Architecture.md) | ⚠️ ADR-008로 대체 |
| ADR | [ADR-002 UI 렌더링 전략](ADR/ADR-002_UI_Rendering_Strategy.md) | ✅ |
| ADR | [ADR-003 AI/NPU 추론](ADR/ADR-003_AI_NPU_Inference_Pipeline.md) | ✅ ADR-009와 함께 적용 |
| ADR | [ADR-004 데이터 레이어](ADR/ADR-004_Data_Layer.md) | ✅ |
| ADR | [ADR-005 시크릿 저장 정책](ADR/ADR-005_Secret_Storage_Policy.md) | ✅ |
| ADR | [ADR-006 백그라운드 실행 모델](ADR/ADR-006_Background_Execution_Model.md) | ✅ |
| ADR | [ADR-007 웹 프레임워크 결정](ADR/ADR-007_Web_Framework_Decision.md) | ✅ |
| ADR | [ADR-008 설치형 배포 전략](ADR/ADR-008_Installer_and_Distribution.md) | ✅ NEW v1.3 |
| ADR | [ADR-009 하드웨어 역량 감지](ADR/ADR-009_Hardware_Capability_Detection.md) | ✅ NEW v1.3 |
| ADR | [ADR-010 파일-폴더 조직 모델](ADR/ADR-010_File_Folder_Organization.md) | ✅ NEW v1.3 |
| Schema | [mc_schema.sql](schema/mc_schema.sql) | ✅ v1.5: incomplete_reasons + 정규화/inbox/에디터 settings |
| State | [task_state.md](state_machines/task_state.md) | ✅ |
| State | [project_state.md](state_machines/project_state.md) | ✅ |
| Env | [Environment_Spec.md](Environment_Spec.md) | ✅ |
| Tech Spec | [TS-01 core-api](tech_specs/TS-01_core_api.md) | ✅ |
| Tech Spec | [TS-02 ai-worker](tech_specs/TS-02_ai_worker.md) | ✅ |
| Tech Spec | [TS-03 integrations](tech_specs/TS-03_integrations.md) | ✅ |
| Screen | [Screen_Spec_Addendum.md](Screen_Spec_Addendum.md) | ✅ v1.3: SC-13/14/SC-06 추가 |
| Trace | [Traceability_Matrix.md](Traceability_Matrix.md) | ✅ v1.5: 43 FR |
| API | [API_Contracts.md](API_Contracts.md) | ✅ v1.5: incomplete-reason API 추가 |
| QA | [QA_Test_Plan.md](QA_Test_Plan.md) | ✅ |
| NFR | [Performance_Budget_and_FMEA.md](Performance_Budget_and_FMEA.md) | ✅ |
| Summary | Design_Summary.md (본 문서) | ✅ v1.5 |

---

## 2. Design Readiness Score (재산정)

> 코덱스 검토 의견 "구현 착수 기준 70~75점"을 솔직 수용. v1.1 보강 후 재산정.

**총점: 87 / 100 → Gate 판정: ✅ PASS (≥80)**

| 항목 | 배점 | v1.0 | v1.1 | 비고 |
|------|------|------|------|------|
| 아키텍처 결정 문서화 (ADR) | 25 | 25 | 25 | ADR 4 → 7. 시크릿/백그라운드/프레임워크 결정 로그 보강 |
| DB 스키마 완성도 | 20 | 19 | 19 | junction(item_github_links) + 4 운영 테이블 추가. 임베딩 차원은 모델 확정 후 결정 -1 |
| 상태 머신 정의 | 15 | 15 | 15 | 변경 없음 |
| 서비스 기술 명세 | 20 | 18 | 16 | Tier 1 신규 컴포넌트 3종(secret-bridge/notifier/ai-worker) TS 분량 부족 -2 추가 차감 |
| 환경 명세 | 10 | 9 | 9 | secret-bridge/notifier 흐름 추가, 프로덕션 배포 체크리스트 Phase 5 위임 -1 |
| BA-Tech 추적성 (D1-02) | 10 | 5 | **10** | Traceability_Matrix.md로 30 FR × 6열 완전 매핑 +5 회복 |
| 운영 가시성·복구성 (NEW 가중) | — | — | -7 | 코덱스 지적 수용 — Inbox/Retry/Diag/Cred 명세는 추가됐으나 PRD 본문 반영 전이라 일부 손실 |
| **합계** | **100** | **91** | **87** | v1.0 91점은 추적성·운영 결함을 미반영한 과대평가. v1.1은 정직한 87점. |

### 점수 정직성에 대한 메모

코덱스가 "92점 자기평가는 구현 기준 70~75"라고 한 지적은 **부분적으로 옳다**:

- **옳은 부분** — 운영 컴포넌트(Inbox/Retry/Diag/Cred), 추적성 표, 임베딩 차원/스키마 정합성 결함은 사실이었다. 이런 결함이 있는 상태의 91점은 과대평가였다.
- **수정 후** — v1.1은 그 결함을 닫았으므로 87점은 적정. 70점대로 더 내릴 필요는 없다.
- **남은 위험** — 신규 FR 4종이 Phase 3 PRD 본문에 역반영되지 않았다. Phase 5 진입 전 PRD 보충 또는 본 매트릭스를 권위 문서로 명시해야 한다.

---

## 3. 잔여 Open Questions

| OQ-ID | 내용 | 상태 |
|-------|------|------|
| OQ-BA-01 | Whisper confidence 0.6 임계값 | TS-02 반영, A/B는 Phase 5 |
| OQ-BA-02 | SC-03 Canvas 2D vs WebGL | ADR-002 Canvas 2D 확정 ✅ |
| OQ-BA-03 | TG polling vs webhook | TS-03 polling 확정 ✅ |
| OQ-D-01 (NEW) | 임베딩 모델: KoE5(384) vs bge-m3(1024) | Phase 5 초기 1주 한국어 회상률 비교 후 결정 |
| OQ-D-02 (NEW) | 신규 FR 4종(INBOX/DIAG/NOTIFY-CTR/SET-CRED) PRD 역반영 | Phase 5 진입 전 BA Writer 보충 1회 |

---

## 4. Phase 5 Coder 전달 사항

### V1.0 화면 우선순위 (코덱스 권고 + iet03 의도 반영, Screen_Spec_Addendum §V1.0 화면 우선순위 재조정)

| 순위 | 화면 | 핵심 가치 |
|------|------|---------|
| 1 | SC-01 Today's Flow | 메인 진입점 |
| 2 | SC-04 Context Panel | 핵심 차별화 |
| 3 | SC-09 Capture Inbox | Triage 통합 (NEW) |
| 4 | SC-07 Morning/Evening | 일일 사이클 |
| 5 | SC-08 + SC-08-Cred | 설정·보안 (NEW 보강) |
| 6 | SC-10 Diagnostics | 운영 신뢰 (NEW) |

### 구현 모듈 순서

```
M1. 데이터 골격
    schema.sql 적용 → migrate.py 검증 → settings 시드
M2. 시크릿 인프라 (ADR-005)
    secret-bridge → secret_set.py CLI → 검증
M3. core-api 기본 CRUD
    items / tags / projects API + Jinja2 템플릿
M4. ai-worker 시작
    embed → STT → silero-VAD 순서
M5. SC-01 Today's Flow + SC-04 Context Panel
M6. SC-09 Capture Inbox + integrations (TG polling)
M7. SC-08-Cred Credential UI + SC-10 Diagnostics
M8. notifier-daemon (ADR-006) + SC-07 Morning/Evening
M9. SC-02 검색 (FTS5 → vec)
M10. 잔여: SC-12 충돌 다이얼로그 (3옵션 단순 버전), SC-08 백업
```

### 기술 유의사항 (변경/보강)

- **시크릿**: `.env`에 토큰 절대 금지 (ADR-005). secret-bridge HTTP 경유.
- **알림**: notifier-daemon이 SQLite read-only로 폴링. core-api/integrations와 별도 트랜잭션.
- **임베딩**: KoE5 기본, 차원 384. bge-m3 채택 시 마이그레이션 v002에서 1024로 재인덱싱.
- **Project Hub 코드**: CLAUDE.md 명시대로 참고만. 신규 코드는 mc_schema.sql 기준 새로 작성.
- **신규 FR 4종**은 Traceability_Matrix.md를 권위 문서로 사용. Phase 5 진입 전 PRD 보충(OQ-D-02) 권장.

### `/design` 스킬 활용 (Phase 4.5 또는 Phase 5 초기)

| 우선 | 화면 | 핵심 시각 과제 |
|-----|------|------------|
| 1 | SC-01 Today's Flow | 타임라인 + 컨텍스트 패널 레이아웃 (Connected·Quiet) |
| 2 | SC-04 Context Panel | 0.5s 펼침 WAAPI + 3섹션 정보 계층 |
| 3 | SC-09 Inbox | 키보드 우선 triage UX (a/r/t) |
| 4 | SC-10 Diagnostics | "Honest" 미감 — 상태 색상·서명·타임스탬프 |

---

## 5. Change Log

| 버전 | 날짜 | 변경 내용 | 변경자 |
|------|------|----------|--------|
| 1.0 | 2026-04-27 | 최초 작성 | Phase 4 Designer |
| 1.1 | 2026-05-04 | 코덱스 외부 검토 반영. ADR-005~007 추가, 6테이블 추가, Screen Spec Addendum, Traceability Matrix 작성. 점수 91→87 정직 재산정. | Phase 4 Designer |
| 1.2 | 2026-05-04 | Tier 1 회색지대 폐쇄: API_Contracts, Performance_Budget_and_FMEA, QA_Test_Plan 추가. | Phase 4 Designer |
| 1.3 | 2026-05-04 | 소속-사업-프로젝트 계층(FR-ORG-01~03), 캘린더뷰(FR-CAL-01), 라벨(FR-LABEL-01), 폴더 구조(FR-FILES-01~02), 설치형 배포(ADR-008), 하드웨어 감지(ADR-009), GDrive 연동 모델(ADR-010) 추가. Docker 제거. FR 30→38. 산출물 총 23종. | Phase 4 Designer |
| 1.4 | 2026-05-04 | Google Calendar 연동 추가. FR-INT-GCAL-01~02, gcal_cache 테이블, GCal API 계약. FR 38→40. | Phase 4 Designer |
| 1.5 | 2026-05-06 | 메모/태그/회고 보강 (iet03 D1~D8 결정). Milkdown 에디터, Memo Lifecycle/Morphing, 미완료 사유 캡처(7카테고리×4결정), 태그 정규화 0.85 임계값, inbox→이동 정책. incomplete_reasons 테이블 신설. FR 40→43. | Phase 4 Designer |
