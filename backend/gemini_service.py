"""Gemini 호출: 받아쓰기와 세 갈래 구분 (docs/02-specs.md 2장)."""
import io
import logging
from functools import lru_cache

from google import genai
from google.genai import types
from pydantic import BaseModel

import config

logger = logging.getLogger(__name__)

TRANSCRIBE_PROMPT = (
    "이 회의 녹취를 한국어로 받아써 줘. 들린 내용만 그대로 옮기고, "
    "설명이나 머리말 없이 받아쓴 본문 텍스트만 출력해."
)

ORGANIZE_PROMPT = """다음 회의 본문을 요약, 결정사항, 할 일 세 갈래로 나눠 줘.

- 요약: 회의 전체를 3~5줄로. 새로운 사실을 지어내지 말 것.
- 결정사항: 「하기로 했다 / 확정 / 승인」 처럼 합의가 끝난 것만. 논의만 하고 안 정한 것은 넣지 말 것.
- 할 일: 담당자와 기한이 드러난 것만. 담당자가 없으면 미정으로 적을 것. 기한은 회의에서 말한 그대로 적고 날짜로 바꾸지 말 것.
- 셋 중 어디에도 안 들어가는 잡담은 버릴 것.

회의 본문:
"""


class GeminiError(Exception):
    """Gemini 호출 실패."""


class TodoItem(BaseModel):
    what: str
    who: str
    when: str


class Organized(BaseModel):
    summary: list[str]
    decisions: list[str]
    todos: list[TodoItem]


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    """클라이언트는 한 번 만들어 재사용한다. 매번 만들면 호출 도중 회수될 수 있다."""
    if not config.GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY 가 .env 에 없습니다")
    return genai.Client(api_key=config.GEMINI_API_KEY)


def transcribe(data: bytes, mime_type: str) -> str:
    """녹취 파일 바이트를 받아쓴 텍스트로 바꾼다."""
    uploaded = None
    try:
        client = get_client()
        uploaded = client.files.upload(
            file=io.BytesIO(data), config=types.UploadFileConfig(mime_type=mime_type)
        )
        response = client.models.generate_content(
            model=config.GEMINI_MODEL, contents=[TRANSCRIBE_PROMPT, uploaded]
        )
        text = (response.text or "").strip()
        if not text:
            raise GeminiError("받아쓰기 결과가 비어 있습니다")
        return text
    except GeminiError:
        raise
    except Exception as exc:
        logger.exception("받아쓰기 실패")
        raise GeminiError(str(exc)) from exc
    finally:
        if uploaded is not None and uploaded.name:
            try:
                get_client().files.delete(name=uploaded.name)
            except Exception:
                logger.warning("업로드한 임시 파일 삭제 실패: %s", uploaded.name)


def organize(body: str) -> dict[str, str]:
    """본문을 summary / decisions / todos 문자열로 나눈다. 실패하면 GeminiError."""
    try:
        response = get_client().models.generate_content(
            model=config.GEMINI_MODEL,
            contents=ORGANIZE_PROMPT + body,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=Organized,
            ),
        )
        parsed = Organized.model_validate_json(response.text)
    except GeminiError:
        raise
    except Exception as exc:
        logger.exception("세 갈래 구분 실패")
        raise GeminiError(str(exc)) from exc

    return {
        "summary": "\n".join(line.strip() for line in parsed.summary if line.strip()),
        "decisions": "\n".join(d.strip() for d in parsed.decisions if d.strip()),
        "todos": "\n".join(
            f"{t.what.strip()} | {t.who.strip() or '미정'} | {t.when.strip()}"
            for t in parsed.todos
            if t.what.strip()
        ),
    }
