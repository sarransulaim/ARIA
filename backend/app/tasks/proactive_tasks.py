import asyncio

from app.workers.celery_app import celery_app


@celery_app.task(
    name="tasks.run_proactive_scan",
    bind=True,
    max_retries=0,
)
def run_proactive_scan(self, session_id: str) -> dict:
    """
    Background proactive insight scan for a session.
    Only does real work when feature_proactive_agent is enabled.
    """
    return asyncio.run(_async_proactive_scan(session_id))


async def _async_proactive_scan(session_id: str) -> dict:
    from app.core.config import settings

    if not settings.feature_proactive_agent:
        return {"skipped": True, "reason": "feature_proactive_agent disabled"}

    from app.agents.proactive_agent import ProactiveAgent
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        try:
            agent = ProactiveAgent(db=db)
            result = await agent.run(
                input={"session_id": session_id},
                session_context={},
            )
            await db.commit()
            return result
        except Exception as exc:
            await db.rollback()
            return {"error": str(exc), "session_id": session_id}
