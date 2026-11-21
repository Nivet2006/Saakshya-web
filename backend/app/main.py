"""FastAPI application entrypoint for ASHA Voice Field Register (Agent 1)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as rest_router
from app.api.ws import ws_router
from app.core.config import get_settings
from app.core.logging import configure_logging, log_event

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    settings = get_settings()
    missing = settings.validate_live_credentials()
    if missing:
        logger.warning(
            "Startup warning: missing live credential env vars: %s (check root .env)",
            ", ".join(missing),
        )
    log_event(
        logger,
        "backend_started",
        env=settings.app_env,
        stt=settings.gnani_stt_model,
        tts=settings.gnani_tts_model,
        llm_provider=settings.llm_provider,
        llm_model=settings.effective_llm_model,
        redact_phi=settings.log_redact_phi,
    )
    yield
    log_event(logger, "backend_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ASHA Voice Field Register — AI Voice & Healthcare Backend",
        version="0.1.0",
        description=(
            "Agent 1 backend providing real-time multilingual streaming voice "
            "(Gnani Prisma v3.0 + LLM + Gnani Timbre v3.0), barge-in, "
            "deterministic danger-sign detection, and visit extraction."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(rest_router)
    app.include_router(ws_router)
    return app


app = create_app()

