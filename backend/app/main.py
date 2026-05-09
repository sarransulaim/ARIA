from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import ARIAError
from app.core.redis_client import close_redis

from app.api.v1.routes import (
    auth,
    connections,
    sessions,
    queries,
    schema,
    outputs,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="ARIA — Analytical Research & Intelligence Assistant",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ARIAError)
async def aria_exception_handler(request: Request, exc: ARIAError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "healthy"}


# Register all routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(connections.router, prefix="/api/v1/connections", tags=["connections"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(queries.router, prefix="/api/v1/analysis", tags=["analysis"])
app.include_router(schema.router, prefix="/api/v1/schema", tags=["schema"])
app.include_router(outputs.router, prefix="/api/v1/outputs", tags=["outputs"])
