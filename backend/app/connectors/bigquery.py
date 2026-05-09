from app.connectors.base import BaseConnector
from app.core.exceptions import QueryExecutionError


class BigQueryConnector(BaseConnector):
    def get_dialect(self) -> str:
        return "bigquery"

    async def test_connection(self) -> dict:
        raise NotImplementedError("BigQuery connector not yet implemented")

    async def execute_query(self, sql: str, params: dict = None) -> dict:
        raise NotImplementedError("BigQuery connector not yet implemented")

    async def get_raw_schema(self) -> dict:
        raise NotImplementedError("BigQuery connector not yet implemented")
