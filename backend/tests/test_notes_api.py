"""docs/05-conventions.md 테스트 매트릭스 13케이스."""
from datetime import datetime

VALID_NOTE = {
    "title": "신규 앱 기획 회의",
    "met_at": "2026-10-07T01:00:00Z",
    "attendees": "김대리, 이주임",
    "body": (
        "신규 앱 출시일을 다음 달 15일로 확정했다. "
        "김대리가 다음 주 금요일까지 디자인 시안을 만들기로 했다. 점심 메뉴는 못 정했다."
    ),
}


def test_create_note(client, gemini_pause):
    """정상 생성: 실제 Gemini 로 세 갈래가 채워진다."""
    response = client.post("/api/notes", json=VALID_NOTE)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] >= 1
    assert data["summary"].strip()
    assert data["met_at"] == "2026-10-07T01:00:00Z"
    assert client.get(f"/api/notes/{data['id']}").json()["summary"] == data["summary"]


def test_list_notes_has_no_body(client, make_meeting):
    make_meeting()
    response = client.get("/api/notes")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert "body" not in items[0]


def test_get_note_has_body(client, make_meeting):
    note_id = make_meeting(body="받아쓴 원문")
    response = client.get(f"/api/notes/{note_id}")
    assert response.status_code == 200
    assert response.json()["body"] == "받아쓴 원문"


def test_update_note(client, make_meeting):
    note_id = make_meeting()
    payload = {
        "title": "수정한 제목",
        "met_at": "2026-10-08T02:00:00Z",
        "attendees": "박과장",
        "body": "수정한 본문",
        "summary": "수정 요약",
        "decisions": "수정 결정",
        "todos": "일 | 박과장 | 내일",
    }
    response = client.put(f"/api/notes/{note_id}", json=payload)
    assert response.status_code == 200
    assert response.json()["title"] == "수정한 제목"
    assert client.get(f"/api/notes/{note_id}").json()["todos"] == "일 | 박과장 | 내일"


def test_delete_note(client, make_meeting):
    note_id = make_meeting()
    assert client.delete(f"/api/notes/{note_id}").status_code == 204
    assert client.get(f"/api/notes/{note_id}").status_code == 404


def test_search_matches_title_and_attendees_only(client, make_meeting):
    make_meeting(title="기획 회의", attendees="김대리", body="무관")
    make_meeting(title="주간 회의", attendees="기획팀 박과장", body="무관")
    make_meeting(title="디자인 회의", attendees="이주임", body="기획 이야기가 본문에만 있음")
    response = client.get("/api/notes", params={"q": "기획"})
    assert response.status_code == 200
    assert sorted(item["title"] for item in response.json()) == ["기획 회의", "주간 회의"]


def test_todos(client, make_meeting):
    make_meeting(title="나중 회의", met_at=datetime(2026, 10, 9), todos="B 작업 | 이주임 | 이번 주 안")
    make_meeting(title="먼저 회의", met_at=datetime(2026, 10, 1), todos="A 작업 | 김대리 | 다음 주 금요일")
    response = client.get("/api/todos")
    assert response.status_code == 200
    todos = response.json()
    assert [t["note_title"] for t in todos] == ["먼저 회의", "나중 회의"]
    assert todos[0] == {
        "what": "A 작업",
        "who": "김대리",
        "when": "다음 주 금요일",
        "note_id": todos[0]["note_id"],
        "note_title": "먼저 회의",
    }


def test_create_without_title_is_400(client):
    payload = {k: v for k, v in VALID_NOTE.items() if k != "title"}
    assert client.post("/api/notes", json=payload).status_code == 400


def test_create_with_bad_met_at_is_400(client):
    payload = {**VALID_NOTE, "met_at": "어제 오후"}
    assert client.post("/api/notes", json=payload).status_code == 400


def test_get_missing_id_is_404(client):
    assert client.get("/api/notes/9999").status_code == 404


def test_create_with_unknown_field_is_422(client):
    payload = {**VALID_NOTE, "unknown": "x"}
    assert client.post("/api/notes", json=payload).status_code == 422


def test_upload_mp4_is_415(client):
    response = client.post("/api/upload", files={"file": ("meeting.mp4", b"data", "video/mp4")})
    assert response.status_code == 415


def test_upload_30mb_is_413(client):
    big = b"0" * (30 * 1024 * 1024)
    response = client.post("/api/upload", files={"file": ("meeting.wav", big, "audio/wav")})
    assert response.status_code == 413
