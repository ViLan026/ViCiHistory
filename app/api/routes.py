from __future__ import annotations

import logging


from fastapi import APIRouter, HTTPException, Request, status, Response

from app.config import settings
from app.exceptions import GeminiServiceError, RetrievalServiceError
from app.schemas.verification import EvidenceMapRequest, EvidenceMapResponse, PdfSourceResponse
from app.services.factory import ServiceContainer
from app.services.source_document_service import SourceDocumentService
from app.schemas.source_view_schema import EvidenceViewRequest, EvidenceViewResponse

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


@router.get("/api/v1/sources/{source_id}/pdf", response_model=PdfSourceResponse)
def get_pdf_source(
    source_id: str,
    request: Request,
) -> PdfSourceResponse:
    try:
        services = get_services(request)

        book_name, url, expires_in = services.storage.get_pdf_url(source_id)

        return PdfSourceResponse(
            source_id=source_id,
            book_name=book_name,
            url=url,
            expires_in=expires_in,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Failed to generate PDF signed URL. source_id=%s", source_id)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Không thể tạo đường dẫn truy cập sử liệu.",
        ) from exc


_source_document_service = SourceDocumentService(settings.GCS_BUCKET_NAME)

@router.get("/sources/{source_id}/pages/{page_number}/image")
def get_source_page_image(source_id: str, page_number: int) -> Response:
    try:
        image = _source_document_service.get_page_image(source_id, page_number)

        return Response(
            content=image,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Source page image failed. source_id=%s page=%s", source_id, page_number)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể tải trang sử liệu.") from exc


@router.post("/sources/{source_id}/evidence-view", response_model=EvidenceViewResponse)
def get_evidence_view(source_id: str, request: EvidenceViewRequest) -> EvidenceViewResponse:
    try:
        pdf_pages, display_pages, pages, highlight_found = _source_document_service.build_evidence_view(
            source_id=source_id,
            source_pages=request.pages,
            evidence_text=request.text,
        )

        return EvidenceViewResponse(
            source_id=source_id,
            source_pages=sorted(set(request.pages)),
            pdf_pages=pdf_pages,
            display_pages=display_pages,
            pages=pages,
            highlight_found=highlight_found,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Evidence source view failed. source_id=%s", source_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể chuẩn bị trang sử liệu.") from exc