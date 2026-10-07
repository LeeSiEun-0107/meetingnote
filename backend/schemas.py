"""요청·응답 스키마. 스펙 외 필드는 extra=forbid 로 막는다."""
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


def _to_naive_utc(value: datetime) -> datetime:
    """시간대가 있으면 UTC 로 바꾸고, 없으면 UTC 로 본다."""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return value.replace(tzinfo=None)


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    met_at: datetime
    attendees: str = ""
    body: str = Field(min_length=1)

    _normalize_met_at = field_validator("met_at")(_to_naive_utc)


class NoteUpdate(NoteCreate):
    summary: str = ""
    decisions: str = ""
    todos: str = ""


class _NoteBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    met_at: datetime
    attendees: str
    summary: str
    decisions: str
    todos: str

    @field_serializer("met_at")
    def _serialize_met_at(self, value: datetime) -> str:
        return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


class NoteListItem(_NoteBase):
    """목록 응답. body 는 제외한다."""


class NoteOut(_NoteBase):
    body: str


class TodoOut(BaseModel):
    what: str
    who: str
    when: str
    note_id: int
    note_title: str


class UploadOut(BaseModel):
    text: str
