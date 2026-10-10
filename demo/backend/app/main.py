from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.services.pipeline_inference import get_inference_service
from app.services.whole_image_inference import get_whole_image_inference_service


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

    whole_image_service = getattr(application.state, "whole_image_inference_service", None)
    if whole_image_service is None:
        whole_image_service = get_whole_image_inference_service()
        application.state.whole_image_inference_service = whole_image_service
    if settings.preload_models and hasattr(whole_image_service, "load"):
        try:
            await asyncio.to_thread(whole_image_service.load)
        except Exception:
            logger.error("API started without a ready whole-image classifier; see model status for details")
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Multimodal Snake Species Identification API",
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
