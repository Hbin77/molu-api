from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.schemas.diagnose import DiagnosisResponse
from app.services.gemini import diagnose_image
from app.services.safety import reinforce_safety

router = APIRouter(prefix="/api/v1", tags=["diagnose"])


@router.post(
    "/diagnose",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_200_OK,
)
async def diagnose(
    image: UploadFile = File(..., description="JPEG/PNG/WebP, ≤10MB"),
    hint: str | None = Form(default=None, description="사용자가 추가로 알려주는 텍스트"),
) -> DiagnosisResponse:
    settings = get_settings()

    if image.content_type not in settings.allowed_mime:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"지원하지 않는 형식입니다: {image.content_type}. "
            f"허용: {', '.join(settings.allowed_mime)}",
        )

    raw = await image.read()
    if len(raw) > settings.max_image_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"이미지가 너무 큽니다 (>{settings.max_image_mb}MB).",
        )
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="빈 이미지입니다.",
        )

    try:
        result = await diagnose_image(raw, image.content_type, hint)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 응답을 해석할 수 없습니다: {e}",
        )
    except Exception as e:  # noqa: BLE001 — upstream errors surface as 502
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI 호출 실패: {type(e).__name__}: {e}",
        )

    return reinforce_safety(result)
