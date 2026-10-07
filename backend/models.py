"""Meeting 모델 (docs/02-specs.md 1장). 필드 8개, 순서 고정."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Meeting(Base):
    __tablename__ = "meetings"
    # 지운 id 를 다시 쓰지 않도록 AUTOINCREMENT 를 실제로 넣는다.
    __table_args__ = {"sqlite_autoincrement": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    met_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # UTC
    attendees: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decisions: Mapped[str] = mapped_column(Text, nullable=False, default="")
    todos: Mapped[str] = mapped_column(Text, nullable=False, default="")
