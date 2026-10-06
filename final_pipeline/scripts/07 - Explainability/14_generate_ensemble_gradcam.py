"""Generate per-fold and averaged MobileViT Grad-CAM visualizations."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("YOLO_CONFIG_DIR", tempfile.gettempdir())

from snake_pipeline.config import SPECIES
from snake_pipeline.ensemble import FoldEnsemble
from snake_pipeline.explainability import (colorize_cam, gradcam_for_class,
                                            map_cam_to_original, overlay_cam,
                                            remove_square_padding)
from snake_pipeline.image_ops import predict_roi
from snake_pipeline.safety import gate


def arguments():
    parser = argparse.ArgumentParser(
        description="Average five independently normalized MobileViT Grad-CAM maps."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--roi", help="Existing classifier ROI image")
    source.add_argument("--image", help="Original image; requires --detector")
    parser.add_argument("--original-image", help="Original corresponding to --roi; requires --bbox")
    parser.add_argument("--bbox", nargs=4, type=int, metavar=("X1", "Y1", "X2", "Y2"),
                        help="ROI coordinates in --original-image")
    parser.add_argument("--detector", help="Primary YOLO segmentation checkpoint for --image")
    parser.add_argument("--secondary-detector", help="Optional final detector retry")
    parser.add_argument("--conf", type=float, default=.25)
    parser.add_argument("--imgsz", type=int, default=512)
    parser.add_argument("--retry-conf", type=float, default=.10)
    parser.add_argument("--retry-imgsz", type=int, default=768)
    parser.add_argument("--context", type=float, default=1.30)
    parser.add_argument("--checkpoints", nargs="+", required=True)
    parser.add_argument("--target-class", help="Optional species name or numeric index; default is ensemble top-1")
    parser.add_argument("--thresholds", help="Optional calibrated safety-gate JSON")
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--alpha", type=float, default=.45)
    return parser.parse_args()


def read_rgb(path: str | Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(ImageOps.exif_transpose(image).convert("RGB"))


def save_rgb(path: Path, rgb: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)):
        raise OSError(f"Could not write {path}")


def extract_with_cascade(args, device_name):
    if not args.detector:
        raise SystemExit("--image requires --detector")
    from ultralytics import YOLO
    original_bgr = cv2.imread(args.image)
    if original_bgr is None:
        raise SystemExit(f"Cannot read {args.image}")
    primary = YOLO(args.detector)
    secondary = YOLO(args.secondary_detector) if args.secondary_detector else None
    try:
        roi = predict_roi(primary, original_bgr, args.conf, args.imgsz, device_name, args.context)
        stage = "primary"
    except ValueError:
        try:
            roi = predict_roi(primary, original_bgr, args.retry_conf, args.retry_imgsz,
                              device_name, args.context)
            stage = "primary_retry"
        except ValueError:
            if secondary is None:
                raise
            roi = predict_roi(secondary, original_bgr, args.retry_conf, args.retry_imgsz,
                              device_name, args.context)
            stage = "secondary_retry"
    return cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB), cv2.cvtColor(roi.image, cv2.COLOR_BGR2RGB), \
        tuple(roi.bbox), roi.confidence, stage, roi.mask


def resolve_target(value, predicted_index):
    if value is None:
        return predicted_index
    try:
        index = int(value)
    except ValueError:
        if value not in SPECIES:
            raise SystemExit(f"Unknown target species {value!r}; choose from {SPECIES}")
        index = SPECIES.index(value)
    if not 0 <= index < len(SPECIES):
        raise SystemExit(f"Target class index must be between 0 and {len(SPECIES) - 1}")
    return index


def main():
    args = arguments()
    if len(args.checkpoints) != 5:
        raise SystemExit(f"Expected five fold checkpoints, received {len(args.checkpoints)}")
    if bool(args.original_image) != bool(args.bbox):
        raise SystemExit("Use --original-image and --bbox together")
    if not 0 <= args.alpha <= 1:
        raise SystemExit("--alpha must be between 0 and 1")

    device_name = args.device if not args.device.startswith("cuda") or torch.cuda.is_available() else "cpu"
    device = torch.device(device_name)
    detector_confidence, detection_stage, mask = None, None, None
    if args.image:
        original_rgb, roi_rgb, bbox, detector_confidence, detection_stage, mask = extract_with_cascade(args, device_name)
    else:
        roi_rgb = read_rgb(args.roi)
        original_rgb = read_rgb(args.original_image) if args.original_image else None
        bbox = tuple(args.bbox) if args.bbox else None

    ensemble = FoldEnsemble(args.checkpoints, device)
    tensor = ensemble.transform(Image.fromarray(roi_rgb)).unsqueeze(0).to(device)
    prediction = ensemble.predict(tensor)
    target_index = resolve_target(args.target_class, prediction["predicted_index"])

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    save_rgb(output / "roi.jpg", roi_rgb)
    fold_cams, fold_details = [], []
    for number, (model, metadata) in enumerate(zip(ensemble.models, ensemble.metadata)):
        cam_square, logits = gradcam_for_class(model, tensor, target_index)
        cam_native = remove_square_padding(cam_square, roi_rgb.shape[1], roi_rgb.shape[0])
        fold_cams.append(cam_native)
        vote = int(np.argmax(logits))
        fold = metadata.get("fold", number)
        save_rgb(output / f"fold_{fold}_heatmap.png", colorize_cam(cam_native))
        save_rgb(output / f"fold_{fold}_overlay.jpg", overlay_cam(roi_rgb, cam_native, args.alpha))
        fold_details.append({"fold": fold, "vote_index": vote, "vote_species": SPECIES[vote],
                             "target_index": target_index, "target_species": SPECIES[target_index]})

    ensemble_cam = np.mean(np.stack(fold_cams), axis=0)
    maximum, minimum = float(ensemble_cam.max()), float(ensemble_cam.min())
    ensemble_cam = ((ensemble_cam - minimum) / max(maximum - minimum, 1e-8)).astype(np.float32)
    save_rgb(output / "ensemble_heatmap.png", colorize_cam(ensemble_cam))
    save_rgb(output / "ensemble_overlay.jpg", overlay_cam(roi_rgb, ensemble_cam, args.alpha))
    np.save(output / "ensemble_cam.npy", ensemble_cam)

    if original_rgb is not None and bbox is not None:
        full_cam, original_overlay = map_cam_to_original(original_rgb, ensemble_cam, bbox, args.alpha)
        save_rgb(output / "original.jpg", original_rgb)
        save_rgb(output / "original_heatmap.png", colorize_cam(full_cam))
        save_rgb(output / "original_overlay.jpg", original_overlay)
    if mask is not None:
        cv2.imwrite(str(output / "healed_mask.png"), np.uint8(mask > 0) * 255)

    if detector_confidence is not None:
        prediction["detector_confidence"] = detector_confidence
        prediction["detection_stage"] = detection_stage
    if args.thresholds:
        thresholds = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
        if detector_confidence is not None:
            decision, reasons = gate(prediction, thresholds)
            prediction.update({"decision": decision, "reasons": reasons})
        else:
            prediction["gate_note"] = "Gate not evaluated because --roi has no detector confidence"
    prediction.update({"gradcam_target_index": target_index,
                       "gradcam_target_species": SPECIES[target_index],
                       "fold_gradcams": fold_details,
                       "bbox": list(bbox) if bbox else None})
    (output / "prediction.json").write_text(json.dumps(prediction, indent=2), encoding="utf-8")
    print(json.dumps(prediction, indent=2))
    print(f"Saved Grad-CAM outputs to {output}")


if __name__ == "__main__":
    main()
