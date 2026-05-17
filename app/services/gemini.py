"""Gemini multimodal client — single-call image diagnosis."""

import json
import logging
import time
import uuid
from pathlib import Path

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.schemas.diagnose import DiagnosisResponse, Safety, Trust

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "diagnose_system.md"
_SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8")


def _client() -> genai.Client:
    return genai.Client(api_key=get_settings().gemini_api_key)


def _trust_action(score: float) -> str:
    if score >= 0.95:
        return "accept"
    if score >= 0.5:
        return "warn_badge"
    return "research_again"


async def diagnose_image(image_bytes: bytes, mime: str, hint: str | None) -> DiagnosisResponse:
    """Call Gemini once with the image + optional hint, parse JSON, normalize."""
    settings = get_settings()
    started = time.perf_counter()

    user_text = (
        f"사용자 힌트: {hint}" if hint else "사용자가 추가로 알려준 정보는 없습니다."
    )

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime),
                types.Part.from_text(text=user_text),
            ],
        )
    ]

    logger.info(
        "Gemini call: model=%s, image_bytes=%d, hint=%r",
        settings.gemini_model,
        len(image_bytes),
        hint,
    )

    try:
        response = _client().models.generate_content(
            model=settings.gemini_model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
    except Exception:
        logger.exception("Gemini generate_content raised")
        raise

    raw = (response.text or "").strip()
    logger.info("Gemini raw response (len=%d): %s", len(raw), raw[:300])

    try:
        data: dict = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini returned non-JSON: {raw[:200]}") from e

    # Normalize fields the model may omit
    data.setdefault("sources", [])
    trust_block = data.get("trust") or {}
    score = float(trust_block.get("score", 0.5))
    trust = Trust(score=score, action=trust_block.get("action") or _trust_action(score))  # type: ignore[arg-type]

    safety_block = data.get("safety") or {}
    safety = Safety(
        triggered=bool(safety_block.get("triggered", False)),
        reason=safety_block.get("reason"),
        action=safety_block.get("action", "proceed"),
    )

    latency_ms = int((time.perf_counter() - started) * 1000)

    return DiagnosisResponse(
        diagnosis_id=str(uuid.uuid4()),
        device=data["device"],
        symptom=data["symptom"],
        technical=data.get("technical", ""),
        difficulty=data.get("difficulty", "medium"),
        estimated_minutes=int(data.get("estimated_minutes", 0)),
        steps=data.get("steps", []),
        safety=safety,
        sources=data.get("sources", []),
        trust=trust,
        latency_ms=latency_ms,
    )
