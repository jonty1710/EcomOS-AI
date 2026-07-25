from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.exceptions import RequestValidationError

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    unhandled_error_handler,
    validation_error_handler,
)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0-phase1",
    description="EcomOS AI backend — Phase 1 (Foundation). Deterministic research engine only, no AI providers wired in.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "phase": "1-foundation",
        "ai_providers_configured": False,
        "supabase_configured": settings.supabase_configured,
    }
