from __future__ import annotations

import logging
import sys
import threading
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

                requested = self.settngs.device
                device_name = requested if not requested.startswith("cuda") or torch.cuda.is_available() else "cpu"
                if device_name != requested:
                    logger.warning("CUDA is unavailable; whole-image classifier is using CPU instead of %s", requested)
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

   