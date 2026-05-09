from typing import Type

from app.connectors.base import BaseConnector
from app.connectors.postgresql import PostgreSQLConnector
from app.core.exceptions import InvalidConnectorTypeError

_REGISTRY: dict[str, Type[BaseConnector]] = {
    "postgresql": PostgreSQLConnector,
    # mysql, snowflake, bigquery, csv — added in Phase 2+ iterations
}


def get_connector(
    connector_type: str,
    connection_config: dict,
    credentials: dict,
) -> BaseConnector:
    cls = _REGISTRY.get(connector_type)
    if cls is None:
        raise InvalidConnectorTypeError(connector_type)
    return cls(connection_config, credentials)


def register_connector(connector_type: str, cls: Type[BaseConnector]) -> None:
    _REGISTRY[connector_type] = cls
