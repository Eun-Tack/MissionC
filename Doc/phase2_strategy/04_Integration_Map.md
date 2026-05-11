# 외부 연동 맵 & 데이터 티어 — MC

> 프로젝트: MC (Mission Control)
> 작성: 2026-04-27 | Strategist v1.0
> 인풋: [Phase 1 Feature](../phase1_interview/02_Feature.md), [Phase 1 Business Rules](../phase1_interview/03_Business_Rules.md), [03_OSS_Toolkit](./03_OSS_Toolkit.md)

---

## 1. 외부 연동 전체 맵

| 도구 | 방향 | 프로토콜 | 적용 버전 | 용도 | 상태 |
|-----|-----|---------|---------|-----|-----|
| **Telegram Bot** | 양방향 | Bot API (polling/webhook) | **V1.0** | 빠른 캡처 (메시지 → MC 태스크), 알림 push | 포함 |
| **GitHub** | 양방향 | REST API (PyGithub) | **V1.0** | 이슈·PR 조회·생성·태스크 연결 | 포함 |
| **Gmail** | 읽기 전용 | Google OAuth 2.0 + Gmail API | **V1.1** | 중요 메일 → MC 컨텍스트 패널 연결 | 예정 |
| **Google Drive** | 쓰기/읽기 | Google OAuth 2.0 + Drive API v3 | **V1.2** | Cold tier 아카이브 + 재활성화 | 예정 |
| **WhatsApp** | — | — | **제외** | Business API 비용·ToS 문제로 제외 | 제외 |

> Gmail + Drive는 동일한 Google OAuth 2.0 토큰 공유 → 로그인 1회.

---

## 2. Telegram 연동 상세 (V1.0)

### FR-INT-TG-01: Telegram → MC 빠른 캡처
- 사용자가 Telegram Bot에 텍스트 전송 → MC가 수신 → 태스크/메모 생성
- 날짜·시간 키워드 있으면 dateutil 파싱 → 스케줄 자동 등록 시도
- 파싱 실패 시 "Inbox" 버킷에 raw 저장 → SC-01 Today's Flow에 표시

### FR-INT-TG-02: MC → Telegram 알림 push
- BR-NOTIFY-01 트리거 발생 시 (마감 임박·충돌) → Bot이 사용자에게 메시지 발송
- 사용자 reply "확인" → MC가 수신 → 알림 상태 dismissed로 변경

---

## 3. GitHub 연동 상세 (V1.0)

### FR-INT-GH-01: 이슈·PR 조회
- 프로젝트 설정에 `github_repo` 연결 → MC가 주기적으로 open 이슈·PR 조회
- 조회 결과 → SQLite `github_items` 테이블에 캐시

### FR-INT-GH-02: 이슈 생성
- SC-04 컨텍스트 패널 또는 Quick Capture에서 "→ GitHub 이슈 생성" 버튼
- 제목·본문·라벨 MC 내에서 작성 → PyGithub API 호출 → 생성된 이슈 ID를 태스크 메타에 연결

---

## 4. Hot / Cold 데이터 티어 (V1.2)

### 4.1 티어 정의

```
Hot  (로컬)  : 활성 프로젝트 .md 원본 + SQLite 풀 인덱스
Cold (Drive) : 아카이브 프로젝트 → Drive 업로드, 로컬 .md 삭제, SQLite 메타만 보존
```

### 4.2 티어 전환 라이프사이클

```
[프로젝트 활성]
    로컬 .md 원본 ─── SQLite 메타+벡터 인덱스
         │
    [아카이브 트리거] (수동 or 프로젝트 완료)
         │
    1. Drive에 .md 업로드 (BR-COLD-01)
    2. 업로드 성공 확인 → 로컬 .md 삭제 (BR-COLD-02)
    3. SQLite: file_location = 'cold', drive_file_id = '...' 기록
    4. 벡터 인덱스·태그·매핑 유지 (BR-COLD-03)
         │
    [Cold 상태]
    검색 쿼리 → 메타데이터·벡터 인덱스 히트 가능
    본문 읽기 → "Drive에서 불러오기" 버튼 (lazy fetch)
         │
    [재활성화]
    Drive에서 .md 다운로드 → 로컬 Hot 경로로 복원 (FR-INT-DR-04)
```

### 4.3 기능 요구사항

| FR ID | 내용 |
|-------|-----|
| **FR-INT-DR-01** | 프로젝트 아카이브 시 선택한 .md → Drive 지정 폴더(MC/archive/)에 업로드 |
| **FR-INT-DR-02** | 업로드 성공 후 로컬 .md 삭제 + SQLite `file_location='cold'`, `drive_file_id` 기록 |
| **FR-INT-DR-03** | Cold 항목 검색 — 메타데이터·태그·벡터 인덱스로 검색 가능; 본문은 lazy |
| **FR-INT-DR-04** | Cold 항목 클릭 시 "Drive에서 불러오기" → 다운로드 → Hot 복원 |

### 4.4 비즈니스 규칙

| BR ID | 규칙 |
|-------|-----|
| **BR-COLD-01** | 아카이브는 반드시 Drive 업로드 성공 확인 후에만 로컬 삭제. 업로드 실패 시 로컬 유지. |
| **BR-COLD-02** | 로컬 삭제는 SQLite `file_location='cold'` 기록 완료 후 수행. |
| **BR-COLD-03** | Cold 전환 후에도 태그·프로젝트 매핑·벡터 임베딩은 SQLite에 유지. 검색 가능 상태 보장. |
| **BR-COLD-04** | 재활성화(Drive → 로컬 복원) 완료 전까지 SQLite `file_location` 변경 금지. |

### 4.5 BR-AUTH-03 (분리)

| BR ID | 규칙 |
|-------|-----|
| **BR-AUTH-03a** | AI 추론 요청을 외부 SaaS (OpenAI API, Claude API 등)로 송신 금지. 모든 AI 추론은 로컬 NPU/iGPU. |
| **BR-AUTH-03b** | 사용자가 명시적으로 동의한 자신의 클라우드 백업(Google Drive)에 데이터 송신은 허용. 초기 설정 시 동의 화면 필수. |

---

## 5. Google OAuth 흐름 (V1.1~V1.2 공용)

```
1. 최초 연동: MC Settings → "Google 계정 연결" 버튼
2. 브라우저 열림 → Google OAuth 2.0 consent screen
3. 스코프 요청:
   - gmail.readonly (V1.1)
   - drive.file (V1.2, MC 생성 파일만)
4. 토큰 수령 → keyring (Windows Credential Store) 저장
5. 이후 자동 갱신 (refresh_token 사용)
```

> `drive.file` 스코프 = MC가 생성한 파일만 접근. Drive 전체 접근(drive) 금지 — BR-AUTH-03b 준수.

---

## 6. Phase 3 BA Writer 전달 사항

- **신규 FR**: FR-INT-TG-01/02, FR-INT-GH-01/02, FR-INT-DR-01~04 → `02_Feature.md`에 통합
- **신규 BR**: BR-COLD-01~04, BR-AUTH-03a/b → `03_Business_Rules.md`에 통합
- **SC 업데이트**: SC-08 Settings에 "Google 계정 연결", "Telegram Bot 연결", "GitHub Repo 연결" 항목 추가
- **V1.0 스코프 확정**: Telegram + GitHub만. Gmail + Drive는 V1.1/V1.2.
