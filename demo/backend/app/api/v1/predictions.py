from __future__ import annotations

import asyncio

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status

from app.core.config import settings
from app.schemas.prediction import ModelStatusResponse, PredictionResponse, WholeImageModelStatusResponse, WholeImagePredictionResponse
from app.services.pipeline_inference import InvalidImageError, PipelineUnavailableError, get_inference_service
from app.services.whole_image_inference import InvalidWholeImageError, WholeImagePipelineUnavailableError, get_whole_image_inference_service


router = APIRouter(prefix="/predictions", tags=["Predictions"])
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp"}


async def _read_bounded(file: UploadFile, maximum: int) -> bytes:
    payload = await file.read(maximum + 1)
    if len(payload) > maximum:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds the {maximum // (1024 * 1024)} MB upload limit",
        )
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded image is empty")
    return payload


@router.get("/status", response_model=ModelStatusResponse, summary="Check model readiness")
async def model_status(request: Request) -> ModelStatusResponse:
    service = getattr(request.app.state, "inference_service", None) or get_inference_service()
    return ModelStatusResponse(**service.status())


@router.get(
    "/whole-image/status",
    response_model=WholeImageModelStatusResponse,
    summary="Check whole-image model readiness",
)
async def whole_image_model_status(request: Request) -> WholeImageModelStatusResponse:
    service = (
        getattr(request.app.state, "whole_image_inference_service", None)
        or get_whole_image_inference_service()
    )
    return WholeImageModelStatusResponse(**service.status())


@router.post(
    "",
    response_model=PredictionResponse,
    summary="Identify a snake from an image",
    responses={
        400: {"description": "The upload is not a valid image"},
        413: {"description": "The upload is too large"},
        415: {"description": "Unsupported image media type"},
        503: {"description": "The model pipeline is unavailable"},
    },
)
async def create_prediction(
    request: Request,
    file: UploadFile = File(...),
    include_mask_overlay: bool = Query(
        False,
        description="Include a base64 JPEG of the raw instance-segmentation mask over the original image",
    ),
    include_roi_crop: bool = Query(
        False,
        description="Include a base64 JPEG of the contextual ROI passed to the classifier",
    ),
    include_gradcam: bool = Query(
        False,
        description="Include the five-model averaged Grad-CAM over the classifier ROI",
    ),
) -> PredictionResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported image types are JPEG, PNG, WebP, and BMP",
        )
    payload = await _read_bounded(file, settings.max_upload_bytes)
    service = getattr(request.app.state, "inference_service", None) or get_inference_service()
    try:
        result = await asyncio.to_thread(
            service.predict,
            payload,
            include_mask_overlay=include_mask_overlay,
            include_roi_crop=include_roi_crop,
            include_gradcam=include_gradcam,
        )
    except InvalidImageError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except PipelineUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Inference failed unexpectedly",
        ) from error
    return PredictionResponse(**result)
