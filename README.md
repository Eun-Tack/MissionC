# Local Project Hub

대표 업무, 연구, 개발을 로컬 폴더와 함께 관리하는 개인용 운영 시스템입니다. 이번 버전은 `SQLite 로컬 DB`와 `브라우저 인터페이스`를 중심으로 구성했습니다.

## 핵심 방향

- 프로젝트는 실제 로컬 폴더와 연결됩니다.
- 로그, 메모, 링크, 할 일이 한 프로젝트 안에서 같이 움직입니다.
- 데이터는 `SQLite`에 저장되어 로컬에서 독립적으로 관리됩니다.
- 인터페이스는 딱딱한 표보다 `운영 조종실` 같은 느낌으로 설계했습니다.
- 노트북의 `GPU`, `NPU` 탐지 결과를 바탕으로 재미있는 로컬 AI 기능 아이디어를 보여줍니다.

## 포함된 기능

- SQLite 기반 프로젝트 저장소
- 브라우저 대시보드
- 프로젝트 생성
- 프로젝트별 Task / Log / Note / Link 빠른 추가
- 프로젝트 상세 흐름 보기
- Task 완료 처리
- CPU / GPU / NPU 탐지
- 하드웨어 기반 확장 아이디어 표시

## 파일 구조

```text
schedule/
  project_hub.py
  static/
    index.html
    styles.css
    app.js
  data/
    project_hub.db
```

## 실행 방법

```powershell
python .\project_hub.py init
python .\project_hub.py seed
python .\project_hub.py serve
```

브라우저에서 아래 주소를 열면 됩니다.

```text
http://127.0.0.1:8765
```

## 자주 쓰는 명령

```powershell
python .\project_hub.py init
python .\project_hub.py seed
python .\project_hub.py serve --port 9000
python .\project_hub.py export
```

## 인터페이스 특징

- 왼쪽 레일: 오늘의 프로젝트 상태, 에너지 평균, 역할별 밸런스, 하드웨어 정보
- 중앙 영역: 실험적인 프로젝트 카드와 상세 흐름 패널
- 하단 캡처 영역: 프로젝트 생성과 Quick Capture

Quick Capture는 선택한 프로젝트에 바로 추가됩니다.

- `Task`: 제목, due 날짜
- `Log`: 요약, `status/progress`
- `Note`: 내용, kind
- `Link`: 라벨, 값

예시:

- Log line2: `working/35`
- Note line2: `decision`
- Task line2: `2026-04-29`

## GPU / NPU 기반 확장 아이디어

현재는 장치 탐지와 아이디어 표시에 집중했지만, 다음 기능으로 자연스럽게 이어질 수 있습니다.

1. 로컬 음성 메모를 프로젝트 인박스로 자동 분류
2. GPU 기반 무드보드 또는 주간 리캡 이미지 생성
3. 최근 작업 흐름을 기반으로 한 Focus Constellation 시각화
4. 폴더 변경 이벤트와 프로젝트 타임라인 자동 연결

## 다음 단계 추천

원하시면 바로 이어서 아래 중 하나로 확장할 수 있습니다.

1. 폴더 감시 자동화: 최근 수정 파일을 프로젝트 활동 로그로 자동 반영
2. 로컬 AI 연결: Whisper / Ollama / ONNX Runtime 같은 로컬 스택 연결
3. 주간 리뷰 모드: 일주일 흐름을 자동 요약하는 화면 추가
4. 관계 그래프 뷰: 프로젝트, 링크, 계정, 문서를 네트워크처럼 연결
