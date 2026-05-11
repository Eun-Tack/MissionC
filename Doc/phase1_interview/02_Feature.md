# 기능 상세 — MC

> 관련: [00_Kickoff.md](./00_Kickoff.md), [01_Users_and_Scenarios.md](./01_Users_and_Scenarios.md)
> 작성: 2026-04-26
> 상태: ✅ **Confirmed (2026-04-26 V1.0 결정 반영)**
>
> 표기: 출처는 항목 단위 [추론] 또는 [iet03]. iet03 직접 언급 항목만 [iet03], 나머지는 [추론].

> ## ⚡ V1.0 / V1.1 / V1.2 분리 결정 (2026-04-26 OQ-05-* 답변)
>
> 이 문서의 V1 라인업은 **권위 있는 최종 분리**가 [06_Summary.md](./06_Summary.md)에 있음. 본 문서의 FR-AI/FR-UX 표는 *후보 도출 과정* 기록으로 보존.
>
> **V1.0 MVP (4~6개월)**: 표준 21 + AI VOICE/SEARCH/TAG (3) + NOTIFY/CONFLICT (2) + BACKUP (1) = **26 FR**
> **V1.1**: + FR-AI-SLOT (Phi-3 mini 단발 추출) + FR-UX-04 Voice Glass UI
> **V1.2**: + FR-UX-01 Time Constellation
> **V2**: AGENT/RAG/SUM/CLUSTER/MOOD, UX-02·03·05·06·07
>
> **신규 V1.0 FR (Step 5 갭에서 편입)**:
> - **FR-NOTIFY-01**: 일정 5분 전 OS 시스템 알림 (디폴트 ON, BR-NOTIFY-01)
> - **FR-CONFLICT-01**: 일정 등록 시 같은 시간대 일정 있으면 경고 (LLM 없이 단순 SQL, BR-CONFLICT-01)
> - **FR-BACKUP-01**: 메뉴에서 JSON export 수동 트리거 (BR-BACKUP-01)
>
> **갱신**: BR-DAY-01 — 회고는 별도 파일 `MC-Notes/YYYY/MM/DD-review.md`로 저장.

---

## 0. 전역 규칙 (모든 FR 공통)

| 항목 | 값 | 출처 |
|------|---|------|
| 권한 | 1인 사용자 — iet03 단독. 권한 분기 없음. | [iet03] |
| 외부 통신 | V1은 GitHub API만 허용. 외부 SaaS 저장 금지. | [iet03] |
| 데이터 무결성 | .md 원본은 single source of truth. MC는 single writer. | [iet03] |
| 응답 시간 | UI 인터랙션 0.5초 이내 기본값 (FR별 별도 표기 없으면 적용) | [추론] |

### 0.1 데이터 연결 모델 (v1.5 추가, D8) [iet03]

> "내 일정 → 프로젝트 데이터 → 메모"를 모두 한 컨텍스트로 묶는 컨셉. 구현 후속(ADR-010)에서 동일 방향으로 확정됨.

| 항목 | 결정 |
|------|------|
| 단일 원본 | **로컬 폴더**(MC-Notes/) — SQLite는 메타·연결만, GDrive는 동기 사본 |
| 연결 좌표계 | **상대 경로 기반** — file_index.path = MC_NOTES_ROOT 기준 상대 경로 |
| 클라우드 동기 | **Google Drive for Desktop** (V1.0, 코드 작성 0줄). MC_NOTES_ROOT를 동기 폴더 안에 두면 자동 백업 |
| API 직접 연동 | V1.1로 이관 (FR-INT-DR-01~04). V1.0은 OS-level 동기로 충분 |
| 일정 ↔ 프로젝트 ↔ 메모 연결 흐름 | items → item_projects → projects.folder_path → file_index.{path,project_id,stage_id} (4-hop, 모두 인덱스됨) |
| 일정 ↔ 단일 .md 직접 연결 | file_index.item_id로 1-hop 가능 (FR-FLOW-03 컨텍스트 패널 활용) |
| 폴더 정책 | 신규 메모는 `MC-Notes/inbox/` 자동 저장 → 정리 시 프로젝트 폴더로 이동 (D7, FR-MEMO-01) |

**핵심 의의**: "내 일정"을 클릭하면 그에 연결된 프로젝트 폴더의 모든 메모·이슈·단계가 컨텍스트 패널 0.5초 안에 노출. 사용자는 "스케줄 → 프로젝트"를 별개 시스템으로 의식하지 않음.

---

## 1. FR-FLOW-* (흐름·뷰)

| FR | 이름 | 입력 | 출력 | 성공 시나리오 | 실패 시나리오 |
|----|------|------|------|------------|------------|
| FR-FLOW-01 | Today's Flow 메인 뷰 | 앱 진입 | 오늘 항목 시간순 + Anytime 묶음 + Quick Capture | 1초 내 렌더 | 데이터 로드 실패 시 마지막 캐시 표시 + "재시도" |
| FR-FLOW-02 | 캘린더 토글 | 토글 클릭 | 같은 데이터의 일/주/월 캘린더 뷰 | 0.5초 내 전환 | — |
| FR-FLOW-03 | 컨텍스트 패널 | 항목 클릭 | 우측 패널: 연결 태그·프로젝트, .md, Git 이슈 | 패널 펼침 | 연결 0개면 "아직 연결된 컨텍스트가 없습니다" 빈 상태 |

**Edge Cases**: 항목 100개 이상 시 가상화 / 시간 미지정 항목은 Anytime 묶음 / 패널 열린 채 항목 변경 시 다음 클릭에 갱신
**BR 후보**: BR-FLOW-01 (시간 미지정 → Anytime), BR-FLOW-02 (컨텍스트 패널은 한 번에 1개)

---

## 2. FR-CAP-* (Quick Capture)

| FR | 이름 | 입력 | 출력 | 성공 | 실패 |
|----|------|------|------|------|------|
| FR-CAP-01 | 한 줄 입력 캡처 | 텍스트 + 객체 타입(자동 분류 또는 단축키) | DB row + 흐름 즉시 반영 | 0.3초 내 표시 | 저장 실패 시 입력 보존 + 토스트 "다시 시도" |
| FR-CAP-02 | 다중 태그 인라인 추가 | 텍스트 내 `#태그명` | mapping row N개 | 자동완성 제안 | 신규 태그 자동 생성 + 확인 |

**Edge Cases**: 빈 입력 거부 / 1만자 초과 시 메모로 강제 분류 / 동일 텍스트 연속 2회 입력 시 중복 확인
**BR 후보**:
- BR-CAP-01 (자동 분류): 시간 패턴(예: `14:00`, `오늘 3시`) → 일정 / `[ ]` 또는 `- todo` → 태스크 / 그 외 → 메모
- BR-CAP-02 (`#태그` 표기로 인라인 태깅 허용)

---

## 3. FR-MEMO-* (메모 / .md)

| FR | 이름 | 입력 | 출력 | 성공 | 실패 |
|----|------|------|------|------|------|
| FR-MEMO-01 | 일자 .md 자동 생성·추가 | 메모 입력 시점 | `MC-Notes/YYYY/MM/DD.md` 신규 또는 append | 파일 OK | 권한 오류 시 폴더 권한 안내 + 임시 큐 |
| FR-MEMO-02 | 자유 명명 .md 생성 | 사용자 명명 + 내용 | 같은 폴더에 자유 파일 | 생성 OK | 동명 충돌 시 `_1`, `_2` 자동 |
| FR-MEMO-03 | LocalDocsHub 연결 안내 | 설정 화면 | 권장 root 경로 표시 + 복사 버튼 | 정보 표시 | (외부 도구 — MC가 자동 변경 X) |
| FR-MEMO-04 | 외부 편집 감지 | 파일 변경 이벤트 | 인덱스 자동 갱신 | 1.5초 디바운스 후 갱신 | 충돌 시 사용자 알림 |
| FR-MEMO-05 | 메타 다중 매핑 | 메모 + 태그·프로젝트 | mapping row N개 | OK | — |

**Edge Cases**: 외부 삭제 시 인덱스 "결손" 마킹 / 외부 편집 도중 파일 잠금 → 디바운스 재시도 / 같은 .md를 여러 태그가 가리킴(정상) / 자정 직전 입력은 오늘 파일에 / 자정 이후는 다음날 파일에
**BR 후보**:
- BR-MEMO-01 (단일 원본 + 메타 다중 매핑) **— [iet03] 직접 언급**
- BR-MEMO-02 (외부 변경은 감지·갱신, MC가 외부 편집 결과를 덮어쓰지 않음)
- BR-MEMO-03 (자정 기준 일자 파일 결정)

---

## 4. FR-PROJ-* (프로젝트 / 태그)

| FR | 이름 | 입력 | 출력 | 성공 | 실패 |
|----|------|------|------|------|------|
| FR-PROJ-01 | 태그 자유 추가 | 항목 + 태그명 | mapping row | 자동완성 | 신규 태그 자동 생성 |
| FR-PROJ-02 | 정식 프로젝트로 마킹 | 태그 ID | 메타 필드 활성화 (vision, priority P0~P3, status, progress) | 마킹 OK | 빈 메타 허용 |
| FR-PROJ-03 | 정식 프로젝트 → 일반 태그 강등 | 프로젝트 ID | 메타 hidden 보존 (재승격 시 복원) | 강등 OK | 데이터 손실 X |
| FR-PROJ-04 | 사후 묶음 (수동 승격) | 항목 N개 + 새 프로젝트명 | 새 프로젝트 + 항목들에 태그 일괄 추가 | 일괄 OK | 부분 실패 시 트랜잭션 롤백 |

**Edge Cases**: 정식 프로젝트가 빈 상태 (모든 항목이 다른 태그로 옮김) — 허용 / 같은 이름의 태그 재생성 시 충돌 → 기존 사용
**BR 후보**:
- BR-PROJ-01 (태그명 unique, 대소문자 무시)
- BR-PROJ-02 (정식 프로젝트 ⊂ 태그 — 모든 정식 프로젝트는 태그지만 그 역은 X) **— [iet03] 모델 직접 언급**
- BR-PROJ-03 (자동 묶음 제안은 V1 제외, V2)

---

## 5. FR-GIT-* (Git 연동)

| FR | 이름 | 입력 | 출력 | 성공 | 실패 |
|----|------|------|------|------|------|
| FR-GIT-01 | GitHub PAT 등록 | PAT | Windows Credential Manager 저장 | 저장 OK + 검증 호출 | PAT 무효 시 "권한 확인" 안내 |
| FR-GIT-02 | 정식 프로젝트에 repo 연결 | 프로젝트 + repo URL | 매핑 저장 | 검증 후 저장 | repo 접근 불가 시 권한 재확인 |
| FR-GIT-03 | 이슈/진척도 조회 | 프로젝트 ID | 이슈 목록 + open/closed/recent activity | API OK | 토큰 만료/네트워크 오류 시 캐시 + 알림 |
| FR-GIT-04 | 자동 동기 캐시 | 주기 (5/15/30분) | 로컬 캐시 갱신 | OK | 오프라인 시 마지막 캐시 표시 |

**Edge Cases**: PAT 만료 / repo 권한 회수 / GitHub Rate Limit / 1000+ 이슈 대형 repo → 페이지네이션
**BR 후보**:
- BR-GIT-01 (PAT 평문 저장 금지 — Credential Manager 강제) **— [iet03] 답변 영역**
- BR-GIT-02 (동기 주기 5/15/30분 사용자 설정, 디폴트 15분)

---

## 6. FR-DAY-* (일별 의식)

| FR | 이름 | 입력 | 출력 | 성공 | 실패 |
|----|------|------|------|------|------|
| FR-DAY-01 | 아침 프리뷰 | 첫 진입 (당일 첫 실행) | 오늘 일정 + 이월 태스크 + 어제 마지막 메모 | 1초 내 | 빈 상태도 인사 표시 |
| FR-DAY-02 | 저녁 회고 화면 | 회고 진입 (수동 또는 시간 트리거) | 오늘 항목 (완료/미완료/지연) + 반성 메모 입력 | 입력 즉시 오늘 .md에 추가 | 입력 보존 |
| FR-DAY-03 | 미완료 이월/보류 | 미완료 항목 + 액션 | 다음 날 또는 보류 | 즉시 반영 | OK |

**Edge Cases**: 회고 안 한 채 다음날 → 어제 회고 진입 옵션 표시 / 0개 완료 / 자정 직전 회고 시 자정 넘김 처리
**BR 후보**:
- BR-DAY-01 (반성 메모는 오늘 .md 파일에 `## 회고` 섹션으로 추가)
- BR-DAY-02 (이월 태스크는 원본 보존, 새 인스턴스 생성 X — 같은 task가 날짜 이동만)

---

# ⚡ 새 영역 — GPU/NPU + UI 혁신 (V1 확정)

> 검토 결과 [iet03] 단순 STT가 아닌 *추론·검색하는 음성 비서*가 진짜 의도. 다중턴 에이전트는 7B 모델 응답 30초+ 위험으로 V2 분리.
> 하드웨어 검사: Intel Core Ultra 7 355 + Intel NPU + iGPU + 32GB RAM (Win11). NPU 본업 = 음성·임베딩·작은 모델 단발 추론.

## 7. FR-AI-* (V1 확정 — 4개)

| FR | 시나리오 | 모델 | 가속 | 상태 |
|----|---------|------|-----|------|
| **FR-AI-VOICE** | 단축키 → 발화 → 텍스트 받아쓰기 → Quick Capture 자동 입력 (등록은 사용자 확인) | Whisper Base ONNX (~74M) | Intel NPU via OpenVINO | ✅ V1 |
| **FR-AI-SEARCH** | 의미 검색. 단어 변형·다른 표현 다 잡음. FTS5와 병행 fallback. | BGE-small-ko 또는 multilingual-e5-small (~120M) | Intel NPU | ✅ V1 |
| **FR-AI-TAG** | 새 메모 작성 시 의미 가까운 기존 항목들의 태그 N개 *제안* (자동 적용 X). 데이터 30개 미만이면 비활성. | SEARCH 임베딩 재사용 | Intel NPU | ✅ V1 |
| **FR-AI-SLOT** | 자유 텍스트 → JSON {time, title, tags, type} 단발 추출. 다중턴/도구 호출 X. 결과 항상 미리보기 후 확인. | Phi-3 mini INT4 ONNX (~2GB) | Intel NPU via OpenVINO | ✅ V1 |

### V2로 미루는 후보 (간결화)

| 미뤄진 항목 | 사유 |
|----------|------|
| FR-AI-AGENT (다중턴 + 도구 호출) | 7B 모델 iGPU 응답 30초+ 위험. V2에서 모델·아키텍처 재평가. |
| FR-AI-RAG (LLM 답변 생성) | SEARCH(임베딩+sqlite-vec)로 V1 검색 가치는 충족. 답변 생성은 V2. |
| FR-AI-SUM (일일 요약) | [iet03 결정] 메모 누적 시 토큰·정확도 부담 누적. V1·V2 모두 보수적으로 제외. |
| FR-AI-CLUSTER (프로젝트 묶음 자동 발견) | 데이터 N개월 누적 후. 사용자 신뢰 깨질 위험. |
| FR-AI-MOOD (이미지 생성) | iGPU에서 SD-Turbo 3~5초/장. 가치 대비 부담. |
| FR-AI-VOICE-RETRO (음성 회고) | FR-AI-VOICE 파이프라인 재사용. V1.5 가벼운 추가 가능. |

**모델 메모리 합계 (V1)**: Whisper Base 0.15GB + BGE-small 0.12GB + Phi-3 mini 2GB ≈ **2.3GB**. 32GB 중 충분. 동시 로드 OK.

## 8. FR-UX-* (V1 확정 — 옵션 B "균형")

| FR | 컨셉 | V1 위치 | 상태 |
|----|------|--------|------|
| **FR-UX-04** | **Voice-driven Glass UI** — 음성 입력 모드 진입 시 반투명 유리 패널 + 음파 시각화. 키보드 fallback 동등. | 음성 입력 시 발동 (V1 시그니처) | ✅ V1 |
| **FR-UX-01** | **Time Constellation** — 24시간 원형 + 별자리 곡선 연결 | 메인 뷰 *토글 옵션* (디폴트는 표준 흐름·캘린더) | ✅ V1 (토글) |
| FR-UX-06 | Ambient Project Pulse | always-on 데이터 누적 후 V2 | V2 |
| FR-UX-02 | Project Gravity (행성-위성) | iGPU 렌더 부담 + 핵심 가치 아님 | V2 |
| FR-UX-03 | Day Heart-rate (ECG) | 데이터 누적 후 가치 ↑ | V2 |
| FR-UX-05 | Spatial Memo Wall | 클러스터 + 캔버스 부담 | V2 |
| FR-UX-07 | Tactile Card Deck | 메인 뷰 패러다임과 충돌 | V2 |

**V1 메인 뷰 구성**: 표준 흐름(타임라인) + 캘린더 토글 + Time Constellation 토글 (3개 뷰 전환). 음성 입력 시 Voice Glass UI 오버레이.

---

## 9. FR-INT-* (외부 연동) — Phase 2 추가

> V1.0: Telegram + GitHub. V1.1: Gmail. V1.2: Google Drive (Cold tier).

| FR | 이름 | 입력 | 출력 | 성공 | 실패 | 버전 |
|----|------|------|------|------|------|------|
| **FR-INT-TG-01** | Telegram → MC 빠른 캡처 | Bot 수신 텍스트 | 태스크/메모 생성 + 날짜 파싱 시 스케줄 등록 | 0.5초 내 DB 저장 | 파싱 실패 → Inbox 버킷 저장 | V1.0 |
| **FR-INT-TG-02** | MC → Telegram 알림 push | BR-NOTIFY-01 트리거 | Bot이 사용자에게 메시지 발송 | 발송 OK | 네트워크 오류 시 큐 + 재시도 | V1.0 |
| **FR-INT-GH-01** | GitHub 이슈·PR 조회 | 프로젝트 linked repo | `github_items` 캐시 갱신 | 캐시 OK | 토큰 만료/Rate Limit → 마지막 캐시 유지 | V1.0 |
| **FR-INT-GH-02** | GitHub 이슈 생성 | 제목·본문·라벨 | 이슈 생성 + 태스크 메타 연결 | 생성 OK | API 오류 시 draft 보존 | V1.0 |
| **FR-INT-DR-01** | Cold tier 아카이브 | 프로젝트 아카이브 액션 | 선택 .md → Drive `MC/archive/` 업로드 | 업로드 확인 | 실패 시 로컬 .md 유지 (BR-COLD-01) | V1.2 |
| **FR-INT-DR-02** | 아카이브 완료 처리 | Drive 업로드 성공 | 로컬 .md 삭제 + SQLite `file_location='cold'` + `drive_file_id` 기록 | DB 갱신 OK | BR-COLD-02 순서 준수 | V1.2 |
| **FR-INT-DR-03** | Cold 항목 검색 | 검색 쿼리 | 메타데이터·태그·벡터 인덱스 결과 + "Drive 본문" lazy 표시 | 검색 결과 정상 | 벡터 인덱스 유실 시 메타 검색 fallback | V1.2 |
| **FR-INT-DR-04** | Cold 항목 재활성화 | 사용자 "불러오기" 클릭 | Drive → 로컬 .md 다운로드 + Hot 복원 | 복원 OK | 다운로드 실패 시 Cold 상태 유지 (BR-COLD-04) | V1.2 |

**BR 연결**: BR-COLD-01~04, BR-AUTH-03a/b ([03_Business_Rules.md](./03_Business_Rules.md) §0.B 참조)

---

## V1 최종 라인업 요약

| 영역 | 항목 수 | 비고 |
|------|------|------|
| 표준 (FLOW/CAP/MEMO/PROJ/GIT/DAY) | 21 FR | Step 1 그대로 |
| AI (NPU) | 3 FR (V1.0) / +1 V1.1 | V1.0: VOICE/SEARCH/TAG; V1.1+: SLOT |
| UX | 1 FR (V1.1) / 1 FR (V1.2) | V1.1: UX-04 Voice Glass; V1.2: UX-01 Constellation |
| 시스템 (NOTIFY/CONFLICT/BACKUP) | 3 FR | V1.0 |
| 외부 연동 (INT) | 4 FR (V1.0) / 4 FR (V1.2) | V1.0: TG-01/02·GH-01/02; V1.1: Gmail; V1.2: DR-01~04 |
| **V1.0 MVP 합계** | **26 FR** | [06_Summary.md](./06_Summary.md) 권위 |

---

## Open Questions (이 단계에서 닫힘)

| OQ-ID | 질문 | 답변·상태 |
|-------|------|---------|
| OQ-02-01 | FR-AI V1 포함 항목 | ✅ Closed — VOICE/SEARCH/TAG/SLOT (4개), SUM 제외 |
| OQ-02-02 | FR-UX V1 포함 항목 | ✅ Closed — UX-04 시그니처 + UX-01 토글 (옵션 B) |
| OQ-02-03 | Quick Capture 자동 분류 사용자 동의 | Open — Step 3에서 결정 (디폴트: 분류 결과 항상 미리보기 후 확인) |
| OQ-02-04 | 정식 프로젝트 메타 필수 필드 | Open — Step 3에서 결정 (디폴트: 모두 선택. 빈 값 허용) |
| OQ-02-05 | Git 동기 디폴트 주기 | Open — Step 3에서 결정 (디폴트: 15분) |
| OQ-02-06 | iet03 노트북 가속기 종류 | ✅ Closed — Intel Core Ultra 7 355 + Intel NPU + iGPU + 32GB |

---

## 다음 단계

→ Step 3 (`03_Business_Rules.md`)에서 모든 BR을 IF-THEN 테이블로 + 능동적 갭 탐지.
