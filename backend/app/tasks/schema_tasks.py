from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.index_schema")
def index_schema(connection_id: str) -> dict:
    raise NotImplementedError
