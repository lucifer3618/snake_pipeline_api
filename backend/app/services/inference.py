from __future__ import annotations

import base64
import json
import logging
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from app.core.config import Settings


logger = logging.getLogger(__name__)


class PipelineUnavailableError(RuntimeError):
    """Raised when inference is requested before the model is available."""


class InvalidImageError(ValueError):
    """Raised when uploaded bytes cannot be decoded as an image."""


class InferenceService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._detector: Any = None
        self._secondary_detector: Any = None
        self._ensemble: Any = None
        self._thresholds: dict[str, float] | None = None
        self._thresholds_source = "unavailable"
        self._device: Any = None
        self._load_error: str | None = None
        self._loading = False
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return (
            self._detector is not None
            and self._secondary_detector is not None
            and self._ensemble is not None
            and self._thresholds is not None
        )

    def status(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "loading": self._loading,
            "device": str(self._device or self.settings.device),
            "detector_count": int(self._detector is not None) + int(self._secondary_detector is not None),
            "classifier_count": len(self._ensemble.models) if self._ensemble is not None else 0,
            "thresholds_source": self._thresholds_source,
            "error": self._load_error,
        }

    def _validate_paths(self) -> None:
        missing = [
            path
            for path in [
                self.settings.detector_path,
                self.settings.secondary_detector_path,
                *self.settings.classifier_paths,
            ]
            if not path.is_file()
        ]
        source = self.settings.pipeline_root / "src"
        if not source.is_dir():
            missing.append(source)
        if missing:
            rendered = ", ".join(str(path) for path in missing)
            raise FileNotFoundError(f"Required pipeline artifact(s) not found: {rendered}")
        if not self.settings.classifier_paths:
            raise ValueError("At least one classifier checkpoint is required")

    def load(self) -> None:
        if self.ready:
            return
        with self._load_lock:
            if self.ready:
                return
            self._loading = True
            self._load_error = None
            try:
                self._validate_paths()
                pipeline_source = str((self.settings.pipeline_root / "src").resolve())
                if pipeline_source not in sys.path:
                    sys.path.insert(0, pipeline_source)
                os.environ.setdefault("YOLO_CONFIG_DIR", tempfile.gettempdir())

                import torch
                from ultralytics import YOLO
                from snake_pipeline.ensemble import FoldEnsemble
                from snake_pipeline.safety import DEFAULT_THRESHOLDS

                requested = self.settings.device
                device_name = requested if not requested.startswith("cuda") or torch.cuda.is_available() else "cpu"
                if device_name != requested:
                    logger.warning("CUDA is unavailable; falling back from %s to CPU", requested)
                self._device = torch.device(device_name)

                if self.settings.thresholds_path.is_file():
                    loaded = json.loads(self.settings.thresholds_path.read_text(encoding="utf-8"))
                    self._thresholds = {**DEFAULT_THRESHOLDS, **loaded}
                    self._thresholds_source = "calibrated"
                else:
                    logger.warning(
                        "Threshold file %s is missing; using pipeline defaults",
                        self.settings.thresholds_path,
                    )
                    self._thresholds = dict(DEFAULT_THRESHOLDS)
                    self._thresholds_source = "defaults"

                self._detector = YOLO(str(self.settings.detector_path))
                self._secondary_detector = YOLO(str(self.settings.secondary_detector_path))
                self._ensemble = FoldEnsemble(
                    [str(path) for path in self.settings.classifier_paths],
                    self._device,
                )
            except Exception as error:
                self._detector = None
                self._secondary_detector = None
                self._ensemble = None
                self._thresholds = None
                self._thresholds_source = "unavailable"
                self._load_error = f"{type(error).__name__}: {error}"
                logger.exception("Unable to load inference pipeline")
                raise
            finally:
                self._loading = False

    @staticmethod
    def _encode_jpeg(image: Any) -> dict[str, str]:
        import cv2

        encoded, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not encoded:
            raise RuntimeError("Could not encode inference image artifact")
        return {
            "media_type": "image/jpeg",
            "data": base64.b64encode(buffer.tobytes()).decode("ascii"),
        }

    @staticmethod
    def _draw_mask_overlay(image: Any, mask: Any, alpha: float = 0.42) -> Any:
        import cv2
        import numpy as np

        if mask.shape != image.shape[:2]:
            mask = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
        selected = mask > 0
        output = image.copy()
        color = np.asarray((0, 215, 255), dtype=np.float32)
        output[selected] = np.clip(
            (1.0 - alpha) * output[selected].astype(np.float32) + alpha * color,
            0,
            255,
        ).astype(np.uint8)
        contours, _ = cv2.findContours(
            selected.astype(np.uint8),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        cv2.drawContours(output, contours, -1, (0, 215, 255), 2, cv2.LINE_AA)
        return output

    @staticmethod
    def _predict_instance_roi(
        detector: Any,
        image: Any,
        confidence: float,
        image_size: int,
        device: str,
        context: float,
    ) -> tuple[Any, Any]:
        import cv2
        import numpy as np
        from snake_pipeline.image_ops import crop_from_mask

        results = detector.predict(
            source=image,
            conf=confidence,
            imgsz=image_size,
            device=device,
            retina_masks=True,
            verbose=False,
        )
        if not results or results[0].masks is None or results[0].boxes is None or not len(results[0].boxes):
            raise ValueError("no snake instance detected")

        result = results[0]
        index = int(result.boxes.conf.argmax().item())
        raw_mask = (result.masks.data[index].cpu().numpy() >= 0.5).astype(np.uint8)
        if raw_mask.shape != image.shape[:2]:
            raw_mask = cv2.resize(
                raw_mask,
                (image.shape[1], image.shape[0]),
                interpolation=cv2.INTER_NEAREST,
            )
        roi = crop_from_mask(image, raw_mask, context)
        roi.confidence = float(result.boxes.conf[index].item())
        return roi, raw_mask

    def predict(
        self,
        image_bytes: bytes,
        *,
        include_mask_overlay: bool = False,
        include_roi_crop: bool = False,
    ) -> dict[str, Any]:
        if not self.ready:
            try:
                self.load()
            except Exception as error:
                raise PipelineUnavailableError(self._load_error or str(error)) from error

        import cv2
        import numpy as np
        from PIL import Image
        from snake_pipeline.safety import gate

        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise InvalidImageError("The uploaded file is not a decodable image")

        started = time.perf_counter()
        with self._inference_lock:
            attempts = (
                (
                    "primary",
                    self._detector,
                    self.settings.detector_confidence,
                    self.settings.detector_image_size,
                ),
                (
                    "primary_retry",
                    self._detector,
                    self.settings.detector_retry_confidence,
                    self.settings.detector_retry_image_size,
                ),
                (
                    "secondary_retry",
                    self._secondary_detector,
                    self.settings.detector_retry_confidence,
                    self.settings.detector_retry_image_size,
                ),
            )
            detector_errors: list[str] = []
            roi = None
            raw_mask = None
            detector_stage = None
            for stage, detector, confidence, image_size in attempts:
                try:
                    roi, raw_mask = self._predict_instance_roi(
                        detector,
                        image,
                        confidence,
                        image_size,
                        str(self._device),
                        self.settings.roi_context,
                    )
                    detector_stage = stage
                    break
                except ValueError as error:
                    detector_errors.append(f"{stage}: {error}")

            if roi is None:
                reason = "; ".join(detector_errors) or "no snake instance detected"
                logger.warning("Detector cascade withheld prediction: %s", reason)
                return {
                    "decision": "WITHHOLD",
                    "reasons": [reason],
                    "processing_ms": round((time.perf_counter() - started) * 1000, 2),
                }

            tensor = self._ensemble.transform(Image.fromarray(cv2.cvtColor(roi.image, cv2.COLOR_BGR2RGB)))
            tensor = tensor.unsqueeze(0).to(self._device)
            result = self._ensemble.predict(tensor)
            result["detector_confidence"] = roi.confidence
            decision, reasons = gate(result, self._thresholds)
            x1, y1, x2, y2 = (int(value) for value in roi.bbox)
            original_height, original_width = image.shape[:2]
            roi_height, roi_width = roi.image.shape[:2]
            original_pixels = int(original_width * original_height)
            roi_pixels = int(roi_width * roi_height)
            reduced_pixels = original_pixels - roi_pixels
            retained_percentage = (roi_pixels / original_pixels) * 100.0
            result.update(
                {
                    "decision": decision,
                    "reasons": reasons,
                    "detector_stage": detector_stage,
                    "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "pixel_reduction": {
                        "original_width": int(original_width),
                        "original_height": int(original_height),
                        "original_pixels": original_pixels,
                        "roi_width": int(roi_width),
                        "roi_height": int(roi_height),
                        "roi_pixels": roi_pixels,
                        "reduced_pixels": reduced_pixels,
                        "retained_percentage": round(retained_percentage, 6),
                        "reduction_percentage": round(100.0 - retained_percentage, 6),
                    },
                    "processing_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            )
            if include_mask_overlay:
                result["mask_overlay"] = self._encode_jpeg(self._draw_mask_overlay(image, raw_mask))
            if include_roi_crop:
                result["roi_crop"] = self._encode_jpeg(roi.image)
            return result


_service: InferenceService | None = None


def get_inference_service(settings: Settings | None = None) -> InferenceService:
    global _service
    if _service is None:
        if settings is None:
            from app.core.config import settings as application_settings

            settings = application_settings
        _service = InferenceService(settings)
    return _service
