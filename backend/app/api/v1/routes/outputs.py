import uuid
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from fastapi import HTTPException
from app.core.exceptions import SessionNotFoundError, StorageError
from app.models.db.models import Presentation, Report
from app.models.schemas.output import (
    OutputJobResponse,
    PresentationRequest,
    PresentationResponse,
    ReportRequest,
    ReportResponse,
    SessionOutputsResponse,
)
from app.services.output_service import OutputService

router = APIRouter()

_MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

_EXT_NAMES = {
    "docx": "report.docx",
    "pdf": "report.pdf",
    "pptx": "presentation.pptx",
}


# ── Reports ────────────────────────────────────────────────────────────────────

@router.post("/report", response_model=OutputJobResponse, status_code=202)
async def create_report(
    payload: ReportRequest,
    db: AsyncSession = Depends(get_db),
) -> OutputJobResponse:
    """
    Kick off async report generation. Returns immediately with report_id and
    status='generating'. Poll GET /report/{report_id} until status='ready'.
    """
    from app.models.db.models import Report as ReportModel
    from app.services.session_service import SessionService

    svc = SessionService(db)
    session = await svc.get_by_id(payload.session_id)
    if not session:
        raise SessionNotFoundError(str(payload.session_id))

    report = ReportModel(
        session_id=payload.session_id,
        title=session.title or "Analysis Report",
        report_format=payload.format,
        status="generating",
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    await db.commit()

    from app.tasks.output_tasks import generate_report as generate_report_task
    generate_report_task.delay(
        str(report.id),
        str(payload.session_id),
        payload.format,
        payload.audience or "",
        payload.focus or "",
    )

    return OutputJobResponse(report_id=report.id, status="generating")


@router.get("/report/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Returns report record with current status."""
    svc = OutputService(db)
    report = await svc.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return ReportResponse.model_validate(report)


@router.get("/report/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Download the generated report file.
    Returns HTTP 425 Too Early if generation is not yet complete.
    """
    svc = OutputService(db)
    report = await svc.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    if report.status != "ready":
        return Response(
            content=f'{{"detail":"Report is not ready yet. Current status: {report.status}"}}',
            status_code=425,
            media_type="application/json",
        )

    file_bytes, mime = await svc.download_file(report.storage_key)
    filename = _EXT_NAMES.get(report.report_format, "report.bin")
    return Response(
        content=file_bytes,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Presentations ──────────────────────────────────────────────────────────────

@router.post("/presentation", response_model=OutputJobResponse, status_code=202)
async def create_presentation(
    payload: PresentationRequest,
    db: AsyncSession = Depends(get_db),
) -> OutputJobResponse:
    """
    Kick off async presentation generation. Returns immediately with
    presentation_id and status='generating'.
    """
    from app.models.db.models import Presentation as PresentationModel
    from app.services.session_service import SessionService

    svc = SessionService(db)
    session = await svc.get_by_id(payload.session_id)
    if not session:
        raise SessionNotFoundError(str(payload.session_id))

    pres = PresentationModel(
        session_id=payload.session_id,
        title=session.title or "Analysis Presentation",
        pres_format=payload.format,
        status="generating",
    )
    db.add(pres)
    await db.flush()
    await db.refresh(pres)
    await db.commit()

    from app.tasks.output_tasks import generate_presentation as generate_presentation_task
    generate_presentation_task.delay(
        str(pres.id),
        str(payload.session_id),
        payload.format,
        payload.audience or "",
        payload.focus or "",
    )

    return OutputJobResponse(presentation_id=pres.id, status="generating")


@router.get("/presentation/{presentation_id}", response_model=PresentationResponse)
async def get_presentation(
    presentation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PresentationResponse:
    """Returns presentation record with current status."""
    svc = OutputService(db)
    pres = await svc.get_presentation(presentation_id)
    if not pres:
        raise HTTPException(status_code=404, detail=f"Presentation {presentation_id} not found")
    return PresentationResponse.model_validate(pres)


@router.get("/presentation/{presentation_id}/download")
async def download_presentation(
    presentation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Download the generated presentation file.
    Returns HTTP 425 Too Early if generation is not yet complete.
    """
    svc = OutputService(db)
    pres = await svc.get_presentation(presentation_id)
    if not pres:
        raise HTTPException(status_code=404, detail=f"Presentation {presentation_id} not found")
    if pres.status != "ready":
        return Response(
            content=f'{{"detail":"Presentation is not ready yet. Current status: {pres.status}"}}',
            status_code=425,
            media_type="application/json",
        )

    file_bytes, mime = await svc.download_file(pres.storage_key)
    filename = _EXT_NAMES.get(pres.pres_format, "presentation.bin")
    return Response(
        content=file_bytes,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Session outputs listing ────────────────────────────────────────────────────

@router.get("/session/{session_id}", response_model=SessionOutputsResponse)
async def list_session_outputs(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionOutputsResponse:
    """Returns all reports and presentations for a session."""
    svc = OutputService(db)
    reports = await svc.list_reports(session_id)
    presentations = await svc.list_presentations(session_id)
    return SessionOutputsResponse(
        reports=[ReportResponse.model_validate(r) for r in reports],
        presentations=[PresentationResponse.model_validate(p) for p in presentations],
    )
