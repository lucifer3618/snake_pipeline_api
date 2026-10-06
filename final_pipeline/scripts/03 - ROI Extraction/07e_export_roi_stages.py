"""Export thesis-ready visualizations of the four ROI-extraction stages.

The detector cascade and ROI processing mirror 07b_build_fixed_detector_dataset.py:
primary pass, higher-resolution primary retry, and optional secondary retry.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("YOLO_CONFIG_DIR", tempfile.gettempdir())

from snake_pipeline.image_ops import crop_from_mask


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export original, predicted-mask, healed-mask, and final-ROI panels."
    )
    parser.add_argument("--image", required=True, help="Input image")
    parser.add_argument("--detector", required=True, help="Primary YOLO segmentation checkpoint")
    parser.add_argument("--secondary-detector", help="Optional final fallback checkpoint")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--device", default="0", help="Ultralytics device, such as 0 or cpu")
    parser.add_argument("--conf", type=float, default=.25, help="Primary-pass confidence")
    parser.add_argument("--imgsz", type=int, default=512, help="Primary-pass image size")
    parser.add_argument("--retry-conf", type=float, default=.10, help="Retry confidence")
    parser.add_argument("--retry-imgsz", type=int, default=768, help="Retry image size")
    parser.add_argument("--context", type=float, default=1.30, help="Proportional ROI context")
    parser.add_argument("--overlay-alpha", type=float, default=.42)
    return parser.parse_args()


def read_bgr(path: str | Path) -> np.ndarray:
    with Image.open(path) as source:
        rgb = np.asarray(ImageOps.exif_transpose(source).convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def predict_mask(model, image: np.ndarray, conf: float, imgsz: int, device: str):
    results = model.predict(
        source=image,
        conf=conf,
        imgsz=imgsz,
        device=device,
        retina_masks=True,
        verbose=False,
    )
    if not results or results[0].masks is None or results[0].boxes is None:
        raise ValueError("no snake instance detected")
    result = results[0]
    if not len(result.boxes):
        raise ValueError("no snake instance detected")

    index = int(result.boxes.conf.argmax().item())
    mask = (result.masks.data[index].cpu().numpy() >= .5).astype(np.uint8)
    if mask.shape != image.shape[:2]:
        mask = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    return mask, float(result.boxes.conf[index].item())


def run_cascade(primary, secondary, image: np.ndarray, args: argparse.Namespace):
    attempts = [
        ("primary", primary, args.conf, args.imgsz),
        ("primary_retry", primary, args.retry_conf, args.retry_imgsz),
    ]
    if secondary is not None:
        attempts.append(("secondary_retry", secondary, args.retry_conf, args.retry_imgsz))

    errors = []
    for stage, model, confidence, image_size in attempts:
        try:
            mask, score = predict_mask(model, image, confidence, image_size, args.device)
            return mask, score, stage
        except ValueError as error:
            errors.append(f"{stage}: {error}")
    raise ValueError("; ".join(errors))


def overlay_mask(image: np.ndarray, mask: np.ndarray, color: tuple[int, int, int], alpha: float):
    output = image.copy()
    selected = mask > 0
    color_array = np.asarray(color, dtype=np.float32)
    output[selected] = np.clip(
        (1.0 - alpha) * output[selected].astype(np.float32) + alpha * color_array,
        0,
        255,
    ).astype(np.uint8)
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(output, contours, -1, color, 2, cv2.LINE_AA)
    return output


def labelled_tile(image: np.ndarray, label: str, width: int = 720, height: int = 500):
    header = 54
    canvas = np.full((height, width, 3), 255, dtype=np.uint8)
    available_height = height - header
    scale = min(width / image.shape[1], available_height / image.shape[0])
    resized = cv2.resize(
        image,
        (max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale))),
        interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
    )
    x = (width - resized.shape[1]) // 2
    y = header + (available_height - resized.shape[0]) // 2
    canvas[y:y + resized.shape[0], x:x + resized.shape[1]] = resized
    cv2.putText(canvas, label, (18, 37), cv2.FONT_HERSHEY_SIMPLEX, .82, (0, 0, 0), 2, cv2.LINE_AA)
    return canvas


def write_image(path: Path, image: np.ndarray) -> None:
    if not cv2.imwrite(str(path), image):
        raise OSError(f"Could not write {path}")


def main() -> None:
    args = arguments()
    if args.context < 1:
        raise SystemExit("--context must be at least 1.0")
    if not 0 <= args.overlay_alpha <= 1:
        raise SystemExit("--overlay-alpha must be between 0 and 1")

    from ultralytics import YOLO

    image_path = Path(args.image)
    if not image_path.is_file():
        raise SystemExit(f"Image not found: {image_path}")
    image = read_bgr(image_path)
    primary = YOLO(args.detector)
    secondary = YOLO(args.secondary_detector) if args.secondary_detector else None

    try:
        predicted_mask, confidence, stage = run_cascade(primary, secondary, image, args)
    except ValueError as error:
        raise SystemExit(f"ROI generation failed after all configured stages: {error}") from error

    # crop_from_mask applies the same healing and context expansion as the dataset builder.
    roi = crop_from_mask(image, predicted_mask, context=args.context, heal=True)
    healed_mask = roi.mask.astype(np.uint8)
    predicted_overlay = overlay_mask(image, predicted_mask, (0, 165, 255), args.overlay_alpha)
    healed_overlay = overlay_mask(image, healed_mask, (0, 180, 0), args.overlay_alpha)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    write_image(output / "01_original.jpg", image)
    write_image(output / "02_predicted_mask_overlay.jpg", predicted_overlay)
    write_image(output / "03_healed_mask_overlay.jpg", healed_overlay)
    write_image(output / "04_context_expanded_roi.jpg", roi.image)
    write_image(output / "02_predicted_mask.png", predicted_mask * 255)
    write_image(output / "03_healed_mask.png", healed_mask * 255)

    tiles = [
        labelled_tile(image, "(a) Original image"),
        labelled_tile(predicted_overlay, "(b) Predicted mask"),
        labelled_tile(healed_overlay, "(c) Healed mask"),
        labelled_tile(roi.image, "(d) Context-expanded ROI"),
    ]
    composite = np.vstack((np.hstack(tiles[:2]), np.hstack(tiles[2:])))
    write_image(output / "05_roi_stages_2x2.jpg", composite)

    metadata = {
        "source_image": str(image_path.resolve()),
        "detection_stage": stage,
        "detector_confidence": confidence,
        "bbox_xyxy": list(roi.bbox),
        "context": args.context,
        "primary_confidence": args.conf,
        "primary_image_size": args.imgsz,
        "retry_confidence": args.retry_conf,
        "retry_image_size": args.retry_imgsz,
    }
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    print(f"Saved ROI-stage visualizations to {output.resolve()}")


if __name__ == "__main__":
    main()
