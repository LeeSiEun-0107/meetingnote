"""테스트 공통 설정. DB 는 테스트마다 임시 파일을 쓰고, Gemini 는 실제로 부른다."""
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import Base, get_db  # noqa: E402
from main import app  # noqa: E402
from models import Meeting  # noqa: E402


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def make_meeting(session_factory):
    """Gemini 를 거치지 않고 DB 에 바로 회의록을 넣는다."""

    def _make(**fields) -> int:
        values = {
            "title": "주간 회의",
            "met_at": datetime(2026, 10, 7, 1, 0, 0),
            "attendees": "김대리, 이주임",
            "body": "본문",
            "summary": "요약",
            "decisions": "결정",
            "todos": "",
        }
        values.update(fields)
        with session_factory() as db:
            meeting = Meeting(**values)
            db.add(meeting)
            db.commit()
            return meeting.id

    return _make


@pytest.fixture()
def gemini_pause():
    """Gemini 를 부르는 테스트가 끝나면 한도에 걸리지 않게 1초 쉰다."""
    yield
    time.sleep(1)
