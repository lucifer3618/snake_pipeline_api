"""Gradient-based class activation maps for the MobileViT ensemble."""
from __future__ import annotations

from contextlib import contextmanager

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torch import nn


def mobilevit_target_layer(model: nn.Module) -> nn.Module:
    """Return the final spatial layer before MobileViT global pooling."""
    backbone = model.features[0]
    final_conv = getattr(backbone, "final_conv", None)
    if final_conv is not None:
        return final_conv
    convolutions = [module for module in backbone.modules() if isinstance(module, nn.Conv2d)]
    if not convolutions:
        raise ValueError("Could not find a spatial convolutional layer for Grad-CAM")
    return convolutions[-1]


@contextmanager
def capture_activations_and_gradients(layer: nn.Module):
    captured: dict[str, torch.Tensor] = {}

    def forward_hook(_module, _inputs, output):
        if not isinstance(output, torch.Tensor) or output.ndim != 4:
            raise ValueError(f"Grad-CAM target must produce BCHW output, received {type(output)}")
        captured["activations"] = output
        output.register_hook(lambda gradient: captured.__setitem__("gradients", gradient))

    handle = layer.register_forward_hook(forward_hook)
    try:
        yield captured
    finally:
        handle.remove()


def normalize_cam(cam: torch.Tensor, epsilon: float = 1e-8) -> torch.Tensor:
    cam = cam - cam.amin(dim=(-2, -1), keepdim=True)
    maximum = cam.amax(dim=(-2, -1), keepdim=True)
    return torch.where(maximum > epsilon, cam / maximum.clamp_min(epsilon), torch.zeros_like(cam))


def gradcam_for_class(
    model: nn.Module,
    tensor: torch.Tensor,
    class_index: int,
    target_layer: nn.Module | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return a normalized input-resolution CAM and species logits for one model."""
    if tensor.ndim != 4 or tensor.shape[0] != 1:
        raise ValueError("Grad-CAM currently expects a batch containing exactly one image")
    layer = target_layer or mobilevit_target_layer(model)
    model.zero_grad(set_to_none=True)
    with torch.enable_grad(), capture_activations_and_gradients(layer) as captured:
        output = model(tensor)
        species_logits = output[0] if isinstance(output, tuple) else output
        if not 0 <= class_index < species_logits.shape[1]:
            raise ValueError(f"Class index {class_index} is outside the model output")
        species_logits[0, class_index].backward()
    activations = captured.get("activations")
    gradients = captured.get("gradients")
    if activations is None or gradients is None:
        raise RuntimeError("Grad-CAM hooks did not capture activations and gradients")
    weights = gradients.mean(dim=(-2, -1), keepdim=True)
    cam = torch.relu((weights * activations).sum(dim=1, keepdim=True))
    cam = F.interpolate(cam, size=tensor.shape[-2:], mode="bilinear", align_corners=False)[:, 0]
    cam = normalize_cam(cam)[0]
    return cam.detach().cpu().numpy().astype(np.float32), species_logits.detach().cpu().numpy()[0]


def remove_square_padding(cam: np.ndarray, roi_width: int, roi_height: int) -> np.ndarray:
    """Map a CAM from the padded classifier square back to native ROI coordinates."""
    square = max(roi_width, roi_height)
    square_cam = cv2.resize(cam, (square, square), interpolation=cv2.INTER_LINEAR)
    left, top = (square - roi_width) // 2, (square - roi_height) // 2
    native = square_cam[top:top + roi_height, left:left + roi_width]
    maximum = float(native.max()) if native.size else 0.0
    if maximum > 1e-8:
        native = (native - float(native.min())) / max(maximum - float(native.min()), 1e-8)
    return native.astype(np.float32)


def colorize_cam(cam: np.ndarray) -> np.ndarray:
    heatmap_bgr = cv2.applyColorMap(np.uint8(np.clip(cam, 0, 1) * 255), cv2.COLORMAP_JET)
    return cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)


def overlay_cam(rgb: np.ndarray, cam: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    if rgb.shape[:2] != cam.shape:
        cam = cv2.resize(cam, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
    heatmap = colorize_cam(cam).astype(np.float32)
    overlay = (1.0 - alpha) * rgb.astype(np.float32) + alpha * heatmap
    return np.clip(overlay, 0, 255).astype(np.uint8)
