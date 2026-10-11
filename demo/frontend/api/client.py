from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class ApiError(RuntimeError):
    """Raised when the prediction API cannot complete a request."""


# Dataclass with not mutuable structure
@dataclass(slots=True)
class SnakeApiClient:
    base_url: str
    api_key: str
    timeout_seconds: int = 180

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")

    @property
    def headers(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key} if self.api_key else {}

    # Main _request internal method that handles all the requests to the API via requests library.
    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                timeout=self.timeout_seconds,
                # Pass any additional keyword arguments to the requests.request method
                **kwargs,
            )
        except requests.RequestException as error:
            raise ApiError(f"Could not reach the inference API: {error}") from error

        # Check if the response is successful, if so, return the response
        if response.ok:
            try:
                return response.json()
            except ValueError as error:
                raise ApiError("The inference API returned an invalid JSON response") from error

        # If the response is not successful, try to extract the error message and raise an ApiError
        try:
            payload = response.json()
            detail = payload.get("detail", payload)
        except ValueError:
            detail = response.text or response.reason
        raise ApiError(f"API request failed ({response.status_code}): {detail}")

    # Make a request to the API to get the status of the pipeline
    def pipeline_status(self) -> dict[str, Any]:
        return self._request("GET", "/predictions/status")

    # Make a request to the API to get the status of the whole image prediction
    def whole_image_status(self) -> dict[str, Any]:
        return self._request("GET", "/predictions/whole-image/status")

    # Make a request to the /predictions endpoint of the API to get pipeline image output
    def predict_pipeline(self, image_bytes: bytes, filename: str,content_type: str, *,include_mask_overlay: bool,
        include_roi_crop: bool, include_gradcam: bool) -> dict[str, Any]:
        return self._request("POST", "/predictions",
            # Parameters for the endpoint to specify which outputs to include in the response
            params={
                "include_mask_overlay": str(include_mask_overlay).lower(),
                "include_roi_crop": str(include_roi_crop).lower(),
                "include_gradcam": str(include_gradcam).lower(),
            },
            files={"file": (filename, image_bytes, content_type)},
        )

    # Make a request to the /predictions/whole-image endpoint of the API to get whole image output
    def predict_whole_image(self, image_bytes: bytes, filename: str, content_type: str, *, 
        include_gradcam: bool) -> dict[str, Any]:
        return self._request("POST", "/predictions/whole-image",
            # Parameters for the endpoint to specify which outputs to include in the response
            params={"include_gradcam": str(include_gradcam).lower()},
            files={"file": (filename, image_bytes, content_type)},
        )
