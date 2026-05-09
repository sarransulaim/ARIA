from abc import ABC, abstractmethod
from typing import Optional


class BaseConnector(ABC):
    def __init__(self, connection_config: dict, credentials: dict):
        self.config = connection_config
        self.credentials = credentials

    @abstractmethod
    async def test_connection(self) -> dict:
        """Returns {success: bool, latency_ms: int, error: str | None}"""

    @abstractmethod
    async def execute_query(self, sql: str, params: Optional[dict] = None) -> dict:
        """Returns {columns: list, rows: list, row_count: int, execution_time_ms: int}"""

    @abstractmethod
    async def get_raw_schema(self) -> dict:
        """Returns full schema dict for Schema Brain"""

    @abstractmethod
    def get_dialect(self) -> str:
        """Returns SQLGlot dialect string: 'postgres', 'mysql', 'snowflake'"""
