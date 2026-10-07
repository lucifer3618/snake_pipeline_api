from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class EncodedImage(BaseModel):
    media_type: Literal["image/jpeg"] = "image/jpeg"
    data: str = Field(description="Base64-encoded image bytes without a data-URL prefix")


class PixelReduction(BaseModel):
    original_width: int
    original_height: int
    original_pixels: int
    roi_width: int
    roi_height: int
    roi_pixels: int
    reduced_pixels: int
    retained_percentage: float
    reduction_percentage: float


class PredictionResponse(BaseModel):
    decision: Literal["ACCEPT", "WITHHOLD"]
    reasons: list[str] = Field(default_factory=list)
    predicted_index: int | None = None
    predicted_species: str | None = None
    species_confidence: float | None = None
    species_margin: float | None = None
    normalized_entropy: float | None = None
    agreement: float | None = None
    member_votes: list[int] | None = None
    predicted_venom: int | None = None
    venom_confidence: float | None = None
    expected_venom: int | None = None
    venom_consistent: bool | None = None
    detector_confidence: float | None = None
    detector_stage: Literal["primary", "primary_retry", "secondary_retry"] | None = None
    bbox: BoundingBox | None = None
    pixel_reduction: PixelReduction | None = None
    mask_overlay: EncodedImage | None = None
    roi_crop: EncodedImage | None = None
    processing_ms: float


class ModelStatusResponse(BaseModel):
    ready: bool
    loading: bool
    device: str
    detector_count: int
    classifier_count: int
    thresholds_source: Literal["calibrated", "defaults", "unavailable"]
    error: str | None = None
