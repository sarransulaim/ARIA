from fastapi import HTTPException, status


class ARIAError(Exception):
    """Base exception for all ARIA errors."""
    status_code: int = 500
    detail: str = "An unexpected error occurred"

    def __init__(self, detail: str = None):
        self.detail = detail or self.__class__.detail
        super().__init__(self.detail)

    def to_http_exception(self) -> HTTPException:
        return HTTPException(status_code=self.status_code, detail=self.detail)


# ── 404 Not Found ──────────────────────────────────────────────────────────────

class ConnectionNotFoundError(ARIAError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, connection_id: str):
        super().__init__(f"Data connection '{connection_id}' not found")


class SessionNotFoundError(ARIAError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, session_id: str):
        super().__init__(f"Session '{session_id}' not found")


class QueryExecutionNotFoundError(ARIAError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, query_id: str):
        super().__init__(f"Query execution '{query_id}' not found")


class UserNotFoundError(ARIAError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, user_id: str):
        super().__init__(f"User '{user_id}' not found")


class ReportNotFoundError(ARIAError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, report_id: str):
        super().__init__(f"Report '{report_id}' not found")


class PresentationNotFoundError(ARIAError):
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, presentation_id: str):
        super().__init__(f"Presentation '{presentation_id}' not found")


# ── 400 Bad Request ────────────────────────────────────────────────────────────

class InvalidSQLError(ARIAError):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str = "The generated SQL is invalid"):
        super().__init__(detail)


class InvalidConnectorTypeError(ARIAError):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, connector_type: str):
        super().__init__(f"Unsupported connector type: '{connector_type}'")


class ConnectionTestFailedError(ARIAError):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, reason: str):
        super().__init__(f"Connection test failed: {reason}")


class ReadOnlyConnectionError(ARIAError):
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self):
        super().__init__("This connection is read-only. Data modification is not allowed.")


# ── 401 / 403 ─────────────────────────────────────────────────────────────────

class AuthenticationError(ARIAError):
    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(detail)


class AuthorizationError(ARIAError):
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, detail: str = "You do not have permission to perform this action"):
        super().__init__(detail)


# ── 422 Unprocessable ──────────────────────────────────────────────────────────

class SchemaIndexingError(ARIAError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(self, detail: str = "Failed to index database schema"):
        super().__init__(detail)


# ── 429 Rate Limit ─────────────────────────────────────────────────────────────

class RateLimitError(ARIAError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self):
        super().__init__("Rate limit exceeded. Please slow down.")


# ── 500 Internal ───────────────────────────────────────────────────────────────

class LLMError(ARIAError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, agent: str, detail: str):
        super().__init__(f"LLM error in {agent}: {detail}")


class EncryptionError(ARIAError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str = "Credential encryption/decryption failed"):
        super().__init__(detail)


class QueryExecutionError(ARIAError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str):
        super().__init__(f"Query execution failed: {detail}")


class StorageError(ARIAError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str = "File storage operation failed"):
        super().__init__(detail)
