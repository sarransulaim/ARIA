from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.generate_report")
def generate_report(session_id: str, report_format: str) -> dict:
    raise NotImplementedError


@celery_app.task(name="tasks.generate_presentation")
def generate_presentation(session_id: str, pres_format: str) -> dict:
    raise NotImplementedError
