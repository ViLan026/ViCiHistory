from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.config import settings
from app.exceptions import GeminiServiceError, RetrievalServiceError
from app.schemas.verification import EvidenceMapRequest, EvidenceMapResponse
from app.services.factory import ServiceContainer

logger = logging.getLogger(__name__)

router = APIRouter()


def get_services(request: Request) -> ServiceContainer:
    services = getattr(request.app.state, "services", None)

    if services is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not ready.",
        )

    return services


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.APP_NAME}


@router.post("/api/v1/evidence-map", response_model=EvidenceMapResponse)
def build_evidence_map(
    request_body: EvidenceMapRequest,
    request: Request,
) -> EvidenceMapResponse:
    try:
        services = get_services(request)

        return services.verifier.build_evidence_map(request_body.content)

    except GeminiServiceError as exc:
        logger.exception("Gemini operation failed. operation=%s", exc.operation)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Dịch vụ phân tích nội dung lịch sử tạm thời không khả dụng.",
        ) from exc

    except RetrievalServiceError as exc:
        logger.exception("Historical evidence retrieval failed.")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dịch vụ truy xuất sử liệu tạm thời không khả dụng.",
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected evidence-map pipeline error.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Đã xảy ra lỗi nội bộ khi tìm nguồn sử liệu.",
        ) from exc