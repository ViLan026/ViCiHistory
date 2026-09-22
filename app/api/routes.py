from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response, status
from app.schemas.evidence import EvidenceMapRequest, EvidenceMapResponse, PdfExcerptRequest

from app.config import settings
from app.exceptions import LLMServiceError, RetrievalServiceError, StorageServiceError
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
    return {
        "status": "ok",
        "service": settings.APP_NAME,
    }


@router.post("/api/v1/evidence-map", response_model=EvidenceMapResponse)
def build_evidence_map(
    request_body: EvidenceMapRequest,
    request: Request,
) -> EvidenceMapResponse:
    try:
        services = get_services(request)
        return services.evidence_map.build_evidence_map(request_body.content)

    except LLMServiceError as exc:
        logger.exception("LLM operation failed. operation=%s", exc.operation)

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

@router.post("/api/v1/sources/{source_id}/excerpt")
def get_source_excerpt(
    source_id: str,
    request_body: PdfExcerptRequest,
    request: Request,
) -> Response:
    try:
        services = get_services(request)

        result = services.source_excerpt.build_excerpt(
            source_id=source_id,
            pdf_pages=request_body.pdf_pages,
            evidence_text=request_body.text,
        )

        return Response(
            content=result.content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{source_id}-excerpt.pdf"',
                "Cache-Control": "no-store",
                "X-Excerpt-Start-Page": str(result.start_pdf_page),
                "X-Excerpt-End-Page": str(result.end_pdf_page),
                "X-Target-Excerpt-Page": str(result.target_excerpt_page),
                "X-Highlight-Mode": result.highlight_mode,
            },
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except StorageServiceError as exc:
        logger.exception("Source PDF storage failed. source_id=%s", source_id)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể tải nguồn sử liệu.",
        ) from exc

    except Exception as exc:
        logger.exception("PDF excerpt generation failed. source_id=%s", source_id)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tạo trích đoạn PDF.",
        ) from exc