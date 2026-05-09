import asyncio
import uuid

from app.workers.celery_app import celery_app


@celery_app.task(
    name="tasks.generate_report",
    bind=True,
    max_retries=1,
    default_retry_delay=5,
)
def generate_report(
    self,
    report_id: str,
    session_id: str,
    report_format: str,
    audience: str,
    focus: str,
) -> dict:
    return asyncio.run(
        _async_generate_report(report_id, session_id, report_format, audience, focus)
    )


@celery_app.task(
    name="tasks.generate_presentation",
    bind=True,
    max_retries=1,
    default_retry_delay=5,
)
def generate_presentation(
    self,
    presentation_id: str,
    session_id: str,
    pres_format: str,
    audience: str,
    focus: str,
) -> dict:
    return asyncio.run(
        _async_generate_presentation(
            presentation_id, session_id, pres_format, audience, focus
        )
    )


async def _async_generate_report(
    report_id: str,
    session_id: str,
    report_format: str,
    audience: str,
    focus: str,
) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.output_service import OutputService

    async with AsyncSessionLocal() as db:
        try:
            svc = OutputService(db=db)
            report = await svc.generate_report(
                session_id=uuid.UUID(session_id),
                report_format=report_format,
                audience=audience or None,
                focus=focus or None,
                report_id=uuid.UUID(report_id),
            )
            await db.commit()
            return {"report_id": str(report.id), "status": report.status}
        except Exception as exc:
            await db.rollback()
            await _mark_report_failed(report_id, str(exc))
            return {"report_id": report_id, "status": "failed", "error": str(exc)}


async def _async_generate_presentation(
    presentation_id: str,
    session_id: str,
    pres_format: str,
    audience: str,
    focus: str,
) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.output_service import OutputService

    async with AsyncSessionLocal() as db:
        try:
            svc = OutputService(db=db)
            pres = await svc.generate_presentation(
                session_id=uuid.UUID(session_id),
                pres_format=pres_format,
                audience=audience or None,
                focus=focus or None,
                presentation_id=uuid.UUID(presentation_id),
            )
            await db.commit()
            return {"presentation_id": str(pres.id), "status": pres.status}
        except Exception as exc:
            await db.rollback()
            await _mark_presentation_failed(presentation_id, str(exc))
            return {"presentation_id": presentation_id, "status": "failed", "error": str(exc)}


async def _mark_report_failed(report_id: str, error: str) -> None:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.db.models import Report

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Report).where(Report.id == uuid.UUID(report_id)))
            report = result.scalar_one_or_none()
            if report:
                report.status = "failed"
                await db.commit()
    except Exception:
        pass


async def _mark_presentation_failed(presentation_id: str, error: str) -> None:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.db.models import Presentation

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Presentation).where(Presentation.id == uuid.UUID(presentation_id))
            )
            pres = result.scalar_one_or_none()
            if pres:
                pres.status = "failed"
                await db.commit()
    except Exception:
        pass
