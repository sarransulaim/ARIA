from app.connectors.base import BaseConnector
from app.core.exceptions import QueryExecutionError


class MySQLConnector(BaseConnector):
    def get_dialect(self) -> str:
        return "mysql"

    async def test_connection(self) -> dict:
        raise NotImplementedError("MySQL connector not yet implemented")

    async def execute_query(self, sql: str, params: dict = None) -> dict:
        raise NotImplementedError("MySQL connector not yet implemented")

    async def get_raw_schema(self) -> dict:
        raise NotImplementedError("MySQL connector not yet implemented")
