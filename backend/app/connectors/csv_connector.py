from app.connectors.base import BaseConnector
from app.core.exceptions import QueryExecutionError


class CSVConnector(BaseConnector):
    def get_dialect(self) -> str:
        return "duckdb"

    async def test_connection(self) -> dict:
        raise NotImplementedError("CSV connector not yet implemented")

    async def execute_query(self, sql: str, params: dict = None) -> dict:
        raise NotImplementedError("CSV connector not yet implemented")

    async def get_raw_schema(self) -> dict:
        raise NotImplementedError("CSV connector not yet implemented")
