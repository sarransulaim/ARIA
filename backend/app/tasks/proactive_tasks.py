from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.run_proactive_scan")
def run_proactive_scan(session_id: str) -> dict:
    raise NotImplementedError
