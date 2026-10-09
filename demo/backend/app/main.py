from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from demo.backend.app.services.pipeline_inference import get_inference_service


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    service = getattr(application.state, "inference_service", None)
    if service is None:
        service = get_inference_service()
        application.state.inference_service = service
    if settings.preload_models and hasattr(service, "load"):
        try:
            await asyncio.to_thread(service.load)
        except Exception:
            logger.error("API started without a ready inference pipeline; see model status for details")
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Final Demo API",
        description="Backend API for model inference and predictions",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    application.include_router(api_router)

    return application


app = create_app()
