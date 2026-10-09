from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PIPELINE_ROOT = BACKEND_ROOT / "pipeline"


def _env_path(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).expanduser().resolve()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError as error:
        raise ValueError(f"{name} must be a number") from error


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# Dataclass decorator allow to reduce boiler plate code and create non mutable class (frozen) with no addtions (slots) as well.
@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    rate_limit_requests: int
    rate_limit_window_seconds: int
    pipeline_root: Path
    detector_path: Path
    secondary_detector_path: Path
    classifier_paths: tuple[Path, ...]
    whole_image_classifier_path: Path
    thresholds_path: Path
    device: str
    detector_confidence: float
    detector_image_size: int
    detector_retry_confidence: float
    detector_retry_image_size: int
    roi_context: float
    max_upload_bytes: int
    preload_models: bool
    cors_origins: tuple[str, ...]

    # classmethod decorator allow the function to run inside the class without relaying on a instance. 
    @classmethod
    def from_env(cls) -> "Settings":
        pipeline_root = _env_path("PIPELINE_ROOT", DEFAULT_PIPELINE_ROOT)
        default_classifier_root = pipeline_root / "models" / "classifiers"
        classifier_value = os.getenv("CLASSIFIER_PATHS")
        classifier_paths = (
            tuple(Path(item.strip()).expanduser().resolve() for item in classifier_value.split(os.pathsep) if item.strip())
            if classifier_value
            else tuple((default_classifier_root / f"fold_{fold}_best.pt").resolve() for fold in range(5))
        )
        origins = tuple(
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
            if origin.strip()
        )
        return cls(
            api_key=os.getenv("API_KEY", "").strip(),
            rate_limit_requests=_env_int("RATE_LIMIT_REQUESTS", 60),
            rate_limit_window_seconds=_env_int("RATE_LIMIT_WINDOW_SECONDS", 60),
            pipeline_root=pipeline_root,
            detector_path=_env_path(
                "DETECTOR_PATH",
                pipeline_root / "models" / "detectors" / "seg_model_s_2_best.pt",
            ),
            secondary_detector_path=_env_path(
                "SECONDARY_DETECTOR_PATH",
                pipeline_root / "models" / "detectors" / "seg_model_n_3_best.pt",
            ),
            classifier_paths=classifier_paths,
            whole_image_classifier_path=_env_path(
                "WHOLE_IMAGE_CLASSIFIER_PATH",
                pipeline_root / "models" / "whole_image" / "whole_image_classifire_MobileViT_fold4.pt",
            ),
            thresholds_path=_env_path("THRESHOLDS_PATH", pipeline_root / "config" / "gate_thresholds.json"),
            device=os.getenv("MODEL_DEVICE", "cuda:0"),
            detector_confidence=_env_float("DETECTOR_CONFIDENCE", 0.25),
            detector_image_size=_env_int("DETECTOR_IMAGE_SIZE", 512),
            detector_retry_confidence=_env_float("DETECTOR_RETRY_CONFIDENCE", 0.10),
            detector_retry_image_size=_env_int("DETECTOR_RETRY_IMAGE_SIZE", 768),
            roi_context=_env_float("ROI_CONTEXT", 1.30),
            max_upload_bytes=_env_int("MAX_UPLOAD_BYTES", 10 * 1024 * 1024),
            preload_models=_env_bool("PRELOAD_MODELS", True),
            cors_origins=origins,
        )


settings = Settings.from_env()
