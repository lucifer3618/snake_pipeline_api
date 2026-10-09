from __future__ import annotations

import logging
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


