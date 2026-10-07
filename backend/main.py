"""MeetingNote API (docs/02-specs.md 4장)."""
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

import config
import gemini_service
from database import Base, engine, get_db
from models import Meeting
from schemas import (
    NoteCreate,
    NoteListItem,
    NoteOut,
    NoteUpdate,
    TodoOut,
    UploadOut,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

MIME_TYPES = {".mp3": "audio/mpeg", ".wav": "audio/wav"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="MeetingNote", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    """검증 실패는 400. 스펙 외 필드만 422 로 남긴다."""
    errors = [
        {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
        for e in exc.errors()
    ]
    has_extra_field = any(e["type"] == "extra_forbidden" for e in exc.errors())
    return JSONResponse(status_code=422 if has_extra_field else 400, content={"detail": errors})


def _get_or_404(db: Session, note_id: int) -> Meeting:
    meeting = db.get(Meeting, note_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="회의록을 찾을 수 없습니다")
    return meeting


def _parse_date(value: str | None, name: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{name} 는 YYYY-MM-DD 형식이어야 합니다")


@app.post("/api/notes", response_model=NoteOut, status_code=201)
def create_note(payload: NoteCreate, db: Session = Depends(get_db)):
    meeting = Meeting(**payload.model_dump())
    try:
        parts = gemini_service.organize(payload.body)
    except gemini_service.GeminiError:
        # 구분에 실패해도 저장은 그대로 한다. 세 갈래는 빈 값으로 둔다.
        parts = {"summary": "", "decisions": "", "todos": ""}
        logger.warning("세 갈래 구분 실패: 빈 값으로 저장합니다")
    meeting.summary = parts["summary"]
    meeting.decisions = parts["decisions"]
    meeting.todos = parts["todos"]
    db.add(meeting)
    db.commit()
    return meeting


@app.get("/api/notes", response_model=list[NoteListItem])
def list_notes(
    q: str | None = None,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
):
    stmt = select(Meeting)
    if q:
        stmt = stmt.where(
            or_(
                Meeting.title.contains(q, autoescape=True),
                Meeting.attendees.contains(q, autoescape=True),
            )
        )
    start = _parse_date(date_from, "from")
    end = _parse_date(date_to, "to")
    if start:
        stmt = stmt.where(Meeting.met_at >= datetime.combine(start, time.min))
    if end:
        # to 는 그날 23:59:59 까지 포함한다.
        stmt = stmt.where(Meeting.met_at < datetime.combine(end + timedelta(days=1), time.min))
    stmt = stmt.order_by(Meeting.met_at.desc(), Meeting.id.desc())
    return db.scalars(stmt).all()


@app.get("/api/notes/{note_id}", response_model=NoteOut)
def get_note(note_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, note_id)


@app.put("/api/notes/{note_id}", response_model=NoteOut)
def update_note(note_id: int, payload: NoteUpdate, db: Session = Depends(get_db)):
    meeting = _get_or_404(db, note_id)
    for field, value in payload.model_dump().items():
        setattr(meeting, field, value)
    db.commit()
    return meeting


@app.delete("/api/notes/{note_id}", status_code=204)
def delete_note(note_id: int, db: Session = Depends(get_db)):
    meeting = _get_or_404(db, note_id)
    db.delete(meeting)
    db.commit()
    return Response(status_code=204)


@app.get("/api/todos", response_model=list[TodoOut])
def list_todos(db: Session = Depends(get_db)):
    """모든 회의의 할 일을 회의 날짜 오래된 순으로 모은다. 기한은 말한 그대로 둔다."""
    meetings = db.scalars(select(Meeting).order_by(Meeting.met_at.asc(), Meeting.id.asc())).all()
    result = []
    for meeting in meetings:
        for line in meeting.todos.splitlines():
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split("|")]
            parts += [""] * (3 - len(parts))
            result.append(
                TodoOut(
                    what=parts[0],
                    who=parts[1] or "미정",
                    when=parts[2],
                    note_id=meeting.id,
                    note_title=meeting.title,
                )
            )
    return result


@app.post("/api/upload", response_model=UploadOut)
def upload_audio(file: UploadFile = File(...)):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in config.ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(status_code=415, detail="mp3, wav 파일만 올릴 수 있습니다")
    data = file.file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="25MB 이하 파일만 올릴 수 있습니다")
    try:
        text = gemini_service.transcribe(data, MIME_TYPES[extension])
    except gemini_service.GeminiError:
        raise HTTPException(status_code=502, detail="받아쓰기에 실패했습니다")
    return UploadOut(text=text)


# 프론트는 같은 오리진에서 제공한다. API 경로를 먼저 등록한 뒤 마지막에 마운트한다.
FRONTEND_DIR = config.BASE_DIR.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
