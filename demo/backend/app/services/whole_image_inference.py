from __future__ import annotations

import base64
import logging
import math
import sys
import threading
import time
from typing import Any

from app.core.config import Settings


logger = logging.getLogger(__name__)


class WholeImagePipelineUnavailableError(RuntimeError):
    """Raised when the whole-image classifier cannot be loaded."""


class InvalidWholeImageError(ValueError):
    """Raised when uploaded bytes cannot be decoded as an image."""


class WholeImageInferenceService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._model: Any = None
        self._metadata: dict[str, Any] | None = None
        self._transform: Any = None
        self._device: Any = None
        self._load_error: str | None = None
        self._loading = False
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()

    @property
    def ready(self) -> bool:
        return self._model is not None and self._metadata is not None and self._transform is not None

    def status(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "loading": self._loading,
            "device": str(self._device or self.settings.device),
            "classifier_count": int(self._model is not None),
            "architecture": self._metadata.get("timm_model") if self._metadata else None,
            "fold": self._metadata.get("fold") if self._metadata else None,
            "error": self._load_error,
        }

    def _validate_paths(self) -> None:
        missing = []
        if not self.settings.whole_image_classifier_path.is_file():
            missing.append(self.settings.whole_image_classifier_path)
        source = self.settings.pipeline_root / "src"
        if not source.is_dir():
            missing.append(source)
        if missing:
            rendered = ", ".join(str(path) for path in missing)
            raise FileNotFoundError(f"Required whole-image artifact(s) not found: {rendered}")

    @staticmethod
    def _validate_metadata(metadata: dict[str, Any]) -> None:
        expected = {
            "model_family": "timm_mobilevit",
            "timm_model": "mobilevit_xs.cvnets_in1k",
            "loss": "arcface_focal",
            "fold": 4,
            "image_size": 256,
            "dual_head": True,
        }
        mismatches = {
            key: (metadata.get(key), value)
            for key, value in expected.items()
            if metadata.get(key) != value
        }
        if mismatches:
            details = ", ".join(
                f"{key}={actual!r} (expected {expected_value!r})"
                for key, (actual, expected_value) in mismatches.items()
            )
            raise ValueError(f"Incompatible whole-image checkpoint metadata: {details}")

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

                import torch
                from snake_pipeline.image_ops import checkpoint_classifier_transform
                from snake_pipeline.models import load_checkpoint

                requested = self.settings.device
                device_name = requested if not requested.startswith("cuda") or torch.cuda.is_available() else "cpu"
                if device_name != requested:
                    logger.warning("CUDA is not available; whole-image classifier is using CPU instead of GPU")
                self._device = torch.device(device_name)

                model, metadata = load_checkpoint(self.settings.whole_image_classifier_path, self._device)
                self._validate_metadata(metadata)
                self._model = model
                self._metadata = metadata
                self._transform = checkpoint_classifier_transform(metadata)
            except Exception as error:
                self._model = None
                self._metadata = None
                self._transform = None
                self._load_error = f"{type(error).__name__}: {error}"
                logger.exception("Unable to load whole-image classifier")
                raise
            finally:
                self._loading = False

    @staticmethod
    def _encode_jpeg(image: Any) -> dict[str, str]:
        import cv2

        encoded, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not encoded:
            raise RuntimeError("Could not encode whole-image inference artifact")
        return {
            "media_type": "image/jpeg",
            "data": base64.b64encode(buffer.tobytes()).decode("ascii"),
        }


    def predict(self, image_bytes: bytes) -> dict[str, Any]:
        if not self.ready:
            try:
                self.load()
            except Exception as error:
                raise WholeImagePipelineUnavailableError(self._load_error or str(error)) from error

        import cv2
        import numpy as np
        import torch
        import torch.nn.functional as F
        from PIL import Image
        from snake_pipeline.config import SPECIES, VENOM_LOOKUP

        image = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise InvalidWholeImageError("The uploaded file is not a decodable image")

        with self._inference_lock:
            # Match the detector-guided timer: exclude model loading, queueing, and decoding.
            started = time.perf_counter()
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            tensor = self._transform(Image.fromarray(image_rgb)).unsqueeze(0).to(self._device)
            with torch.no_grad():
                species_logits, venom_logits = self._model(tensor)
                species_probs = F.softmax(species_logits, dim=1)[0]
                venom_probs = F.softmax(venom_logits, dim=1)[0]

            predicted_index = int(species_probs.argmax())
            predicted_venom = int(venom_probs.argmax())
            top2 = species_probs.topk(2)
            normalized_entropy = float(
                -(species_probs * torch.log(species_probs.clamp_min(1e-9))).sum() / math.log(len(SPECIES))
            )
            expected_venom = int(VENOM_LOOKUP[predicted_index])
            result: dict[str, Any] = {
                "inference_mode": "whole_image_single_model",
                "architecture": "mobilevit_xs.cvnets_in1k",
                "loss": "arcface_focal",
                "fold": 4,
                "model_count": 1,
                "image_size": 256,
                "predicted_index": predicted_index,
                "predicted_species": SPECIES[predicted_index],
                "species_confidence": float(top2.values[0]),
                "species_margin": float(top2.values[0] - top2.values[1]),
                "normalized_entropy": normalized_entropy,
                "predicted_venom": predicted_venom,
                "venom_confidence": float(venom_probs[predicted_venom]),
                "expected_venom": expected_venom,
                "venom_consistent": predicted_venom == expected_venom,
            }
            result["processing_ms"] = round((time.perf_counter() - started) * 1000, 2)

            return result


_whole_image_service: WholeImageInferenceService | None = None
