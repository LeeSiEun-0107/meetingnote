# 04. Tasks

MVP 를 3개 Phase 로 진행한다. Phase 이름과 개수는 고정이며 변경하지 않는다.

| Phase | 이름 | 내용 | 단계 수 |
| --- | --- | --- | --- |
| 1 | 설계 | CLAUDE.md + docs/ 6종 작성 | 10 |
| 2 | 백엔드 | `backend/` FastAPI > API 7개 + 받아쓰기 > Swagger 확인 | 10 |
| 3 | 프론트 | `frontend/` HTML + JS + Tailwind > 화면 4종 > API 연결 > git push | 8 |

## 진행 규칙

- 순서대로만 진행한다. 병렬로 하지 않는다.
- 단계마다 검증 방법으로 확인한 뒤 완료 처리한다.
- 완료 열은 `[ ]` 로 두고, 진행하면서 `[x]` 로 바꾼다.
- "backend 진행해" = Phase 2 전체, "frontend 진행해" = Phase 3 전체.
- 서버 포트는 **8000** 으로 고정한다.

## Phase 1 (설계)

| 단계 | 검증 방법 | 완료 |
| --- | --- | --- |
| 1.1 CLAUDE.md 작성 (역할·기술 스택·작업 절차·절대규칙) | 4개 섹션이 모두 있고 docs 파일명·순서가 일치 | [x] |
| 1.2 `.env` 와 `.gitignore` 준비 | `.env` 에 `GEMINI_API_KEY`, `GEMINI_MODEL` 이 있고 `.gitignore` 에 `.env` 포함 | [x] |
| 1.3 docs/ 6개 파일 생성 | `docs/` 에 지정된 6개 이름만 존재 | [x] |
| 1.4 `docs/화면구성.pdf` 배치 | 파일이 `docs/` 에 있고 5쪽이 열림 | [x] |
| 1.5 00-overview.md 작성 | 매핑표·읽는 순서·화면 4종·id 표 확인 | [x] |
| 1.6 01-product.md 작성 | 목표·페르소나·MVP·확장·범위 외·성공 기준 확인 | [x] |
| 1.7 02-specs.md 작성 | 모델 8필드·API 7개·검증 코드·검색 규칙 확인 | [x] |
| 1.8 03-design.md 작성 | 8행 표와 의존성 정책, id 가 PDF 5쪽과 일치 | [x] |
| 1.9 04-tasks.md 작성 | 3개 Phase 와 단계 수(10 / 10 / 8)가 일치 | [x] |
| 1.10 05-conventions.md 작성 + 첫 커밋 | `git log` 에 `docs: CLAUDE.md + docs 6종 작성` 커밋이 있음 | [x] |

## Phase 2 (백엔드)

의존성은 아래 8개로 한정한다. 이 목록 밖은 추가하지 않는다.

`fastapi`, `uvicorn`, `sqlalchemy`, `pytest`, `httpx`, `google-genai`, `python-multipart`, `python-dotenv`

pytest 실행 시 httpx2 설치 권고가 떠도 무시한다.

| 단계 | 검증 방법 | 완료 |
| --- | --- | --- |
| 2.1 `backend/` 폴더, 가상환경, 의존성 8개 설치 | 가상환경에서 8개 패키지 import 가 성공 | [x] |
| 2.2 `.env` 읽기 설정 (`GEMINI_API_KEY`, `GEMINI_MODEL`) | 코드에 키 문자열이 없고 `os.getenv` 로 읽힘 | [x] |
| 2.3 DB 와 Meeting 모델 (8필드, `AUTOINCREMENT`) | 테이블 DDL 에 `AUTOINCREMENT` 가 있고, 행을 지운 뒤 새로 넣으면 id 가 재사용되지 않음 | [x] |
| 2.4 요청·응답 스키마(`extra="forbid"`)와 400 예외 핸들러 | 필수 필드 누락은 400, 스펙 외 필드는 422 | [x] |
| 2.5 notes 5개 API (생성·목록·단건·수정·삭제) | 상태 코드 201 / 200 / 200 / 200 / 204, 목록엔 `body` 없음, PUT 은 `id` 를 뺀 전 필드를 받음, 없는 id 는 404 | [x] |
| 2.6 검색(`q`, `from`, `to`)과 `GET /api/todos` | 제목·참석자만 부분 일치, `to` 는 23:59:59 까지, todos 는 회의 날짜 오래된 순 | [x] |
| 2.7 `POST /api/upload` + 받아쓰기(Gemini) | 실제 mp3 로 본문 텍스트 반환, mp4 는 415, 30MB 는 413, 외부 호출 실패는 502 | [x] |
| 2.8 세 갈래 구분(Gemini)과 구분 실패 처리 | 실제 호출로 요약·결정사항·할 일 저장, 실패 시 201 이고 세 필드가 빈 값 | [x] |
| 2.9 pytest 13케이스 (`05-conventions.md` 매트릭스) | `pytest` 전체 통과 | [x] |
| 2.10 서버 실행(포트 8000)과 Swagger 확인 | `http://localhost:8000/docs` 에서 `/api/` 7개 경로가 보임 | [x] |

## Phase 3 (프론트)

화면 4종은 `02-specs.md` 화면 명세와 `03-design.md` 표대로 만든다.

| 단계 | 검증 방법 | 완료 |
| --- | --- | --- |
| 3.1 `frontend/index.html`, `app.js` 뼈대, 공통 헤더·탭·테마 토글 | 백엔드(8000)가 같은 오리진에서 제공하고, 테마가 새로고침 뒤에도 유지되며 첫 값은 시스템 설정을 따름 | [x] |
| 3.2 목록 화면 | 카드 2열(360px 에서 1열), 검색 입력 시 다시 조회, 카드 클릭 시 상세 | [x] |
| 3.3 넣기 화면 | 파일 받아쓰기로 본문이 채워지고, 정리하기로 세 칸이 표시됨 | [x] |
| 3.4 상세 화면(겹침 창) | 바깥 영역 클릭 시 닫힘, 제목 수정은 PUT, 삭제는 한 번 더 눌러야 DELETE | [x] |
| 3.5 할 일 화면 | 담당자·기한·회의 표시, 좁은 화면에서 표만 가로 스크롤 | [x] |
| 3.6 요소 이름 대조 | `index.html`·`app.js` 의 id 가 `03-design.md` 7행 표와 정확히 같음 | [x] |
| 3.7 API 연결과 최종 확인 | 녹취 하나가 세 갈래로 저장되고 새로고침해도 유지, 360px 에서 안 깨짐, 검색으로 지난 회의를 찾음 | [x] |
| 3.8 git push | 원격 저장소에서 커밋이 보임 | [x] |
