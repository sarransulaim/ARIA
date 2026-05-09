from app.workers.celery_app import celery_app


@celery_app.task(name="tasks.execute_query")
def execute_query(query_execution_id: str) -> dict:
    raise NotImplementedError
