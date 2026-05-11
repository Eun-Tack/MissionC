# ADR-010: 파일-폴더 조직 모델 및 Google Drive 연동

> 날짜: 2026-05-04 | 상태: Accepted
> 결정자: iet03 | 맥락: Phase 4 v1.3 — 단일 원본 + 폴더 계층 + GDrive 연동

---

## 배경

데이터 원본을 하나로 유지하면서 로컬 폴더와 Google Drive에서도 파일을 찾을 수 있어야 한다. 프로젝트와 단계(Stage)별로 폴더가 정리되어 있으면 MC 밖에서도 파일을 탐색·편집할 수 있다.

---

## 결정

### 데이터 레이어 분리 원칙

```
파일 (Source of Truth) = 로컬 폴더 MC-Notes/
  ↑ watchdog 감지
SQLite (Connection Layer) = 메타데이터 + 연결망
  ↑ Drive for Desktop 동기화 (V1.0 — MC 개입 없음)
Google Drive (Sync Layer) = MC-Notes/ 미러
```

**SQLite는 파일의 존재를 인덱싱하지만 파일의 원본이 아니다.**
파일 삭제 → SQLite는 `file_index.state='missing'` 마킹. 파일은 SQLite 삭제로 사라지지 않는다.

### 폴더 구조 규칙

```
%APPDATA%\MC\                    설정·DB·모델
  mc.db
  models/

{MC_NOTES_ROOT}/                 사용자 지정 (설정에서 변경 가능, 기본 ~/Documents/MC-Notes)
  {Organization}/
    {Business}/
      {Project}/
        {NN_StageName}/          NN = 두 자리 순서 (01, 02, ...)
          파일들.md
  무소속/
    {YYYY}/{MM}/
      DD.md                      일별 메모
    자유파일.md
  .assets/
    logos/
      {org_id}.{ext}
```

### 폴더명 변환 규칙

| 원본 이름 | 변환 규칙 | 예시 |
|---------|---------|------|
| 특수문자 `/\:*?"<>|` | `-` 로 치환 | `플링크/케어` → `플링크-케어` |
| 앞뒤 공백 | trim | `" 프로젝트 "` → `프로젝트` |
| 연속 공백 | 단일 `-` | `MC  개발` → `MC-개발` |
| 대소문자 | 유지 | |

### Google Drive 연동 전략

**V1.0 — Drive for Desktop (MC 개발 없음)**

사용자가 Google Drive for Desktop을 설치하고 `MC-Notes/` 폴더를 Drive 동기화 폴더 안에 두면 자동 미러링된다. MC는 별도 Drive API 호출 없음.

설정 화면(SC-08)에서 안내:
```
"Google Drive 동기화를 원하면:
1. Google Drive for Desktop 설치
2. MC-Notes 폴더를 Google Drive 동기화 폴더로 이동
3. 아래에서 새 경로를 MC-Notes 경로로 설정"
```

**V1.1 — Drive API 직접 연동 (선택)**

- 프로젝트 생성 시 Drive에도 폴더 자동 생성
- 파일 저장 시 Drive 업로드
- FR-INT-DR-01~04 (기존 V1.2 → V1.1로 당김)

### 경로 추상화

코드에서 절대 경로 하드코딩 금지. 모든 파일 경로는 `MC_NOTES_ROOT` 상대 경로로 저장:

```python
# settings에서 읽기
MC_NOTES_ROOT = settings.get("mc_notes_root") or Path.home() / "Documents" / "MC-Notes"

# file_index.path 는 항상 상대 경로
# 예: "플링크데이터/플링크케어-사업/MC-개발/02_개발/스펙.md"
def abs_path(relative: str) -> Path:
    return MC_NOTES_ROOT / relative
```

### 이름 변경 처리 (BR-FILES-03)

소속·사업·프로젝트·단계 이름 변경 시:
1. 기존 폴더 rename
2. `file_index`의 모든 관련 경로 prefix 일괄 치환 (DB 트랜잭션)
3. watchdog 일시 중지 → rename → 재개 (오탐 방지)

---

## 영향

- `file_index` 테이블: `project_id`, `stage_id` 컬럼 추가
- `projects` 테이블: `folder_path` 컬럼 추가
- `project_stages` 테이블: `folder_path` 컬럼 포함 신규 생성
- `settings` 테이블 시드: `mc_notes_root`, `gdrive_enabled` 추가
- core-api: `watchdog` 경로 `MC_NOTES_ROOT` 기준으로 동적 설정

---

## Change Log

| 날짜 | 변경 |
|------|------|
| 2026-05-04 | 최초 작성 |
