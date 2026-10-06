"""Build five-fold classifier ROI folders using one frozen segmentation model.

No segmentation labels are required. Species targets come from the standardized
images' class folders and the already-created split manifest.
"""
import argparse
import csv
import os
import shutil
import tempfile
import sys
from pathlib import Path

import cv2

os.environ.setdefault("YOLO_CONFIG_DIR", tempfile.gettempdir())
from ultralytics import YOLO

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from snake_pipeline.image_ops import predict_roi


def link_or_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def roles_for(row: dict, folds: list[int]):
    if row["split"] == "train_pool":
        held_out = int(row["fold"])
        for fold in folds:
            yield fold, "validation" if fold == held_out else "train"
    else:
        # Calibration and test are fold-independent and needed only once.
        yield 0, row["split"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--images", required=True)
    parser.add_argument("--detector", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="0")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--imgsz", type=int, default=512)
    parser.add_argument("--retry-conf", type=float, help="Lower-confidence retry after the primary pass fails")
    parser.add_argument("--retry-imgsz", type=int, default=768)
    parser.add_argument("--secondary-detector", help="Optional checkpoint used only after both primary attempts fail")
    parser.add_argument("--context", type=float, default=1.30)
    args = parser.parse_args()

    image_root, output = Path(args.images), Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Output must be empty: {output}")
    with open(args.manifest, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    folds = sorted({int(row["fold"]) for row in rows if row["split"] == "train_pool"})
    if folds != [0, 1, 2, 3, 4]:
        raise SystemExit(f"Expected folds 0-4, found {folds}")

    model, audit = YOLO(args.detector), []
    secondary = YOLO(args.secondary_detector) if args.secondary_detector else None
    cache = output / "_native_roi_cache"
    for index, row in enumerate(rows, 1):
        source = image_root / Path(row["relative_path"])
        image = cv2.imread(str(source))
        status, confidence, stage, cached = "", "", "", cache / row["class_name"] / source.name
        try:
            if image is None:
                raise ValueError("image could not be read")
            try:
                roi = predict_roi(model, image, args.conf, args.imgsz, args.device, args.context)
                stage = "primary"
            except ValueError:
                if args.retry_conf is None:
                    raise
                try:
                    roi = predict_roi(model, image, args.retry_conf, args.retry_imgsz, args.device, args.context)
                    stage = "primary_retry"
                except ValueError:
                    if secondary is None:
                        raise
                    roi = predict_roi(secondary, image, args.retry_conf, args.retry_imgsz,
                                      args.device, args.context)
                    stage = "secondary_retry"
            cached.parent.mkdir(parents=True, exist_ok=True)
            if not cv2.imwrite(str(cached), roi.image):
                raise ValueError("ROI could not be written")
            status, confidence = "ok", roi.confidence
        except Exception as error:
            status = f"failed:{error}"

        for fold, role in roles_for(row, folds):
            destination = output / "predicted_roi" / f"fold_{fold}" / role / row["class_name"] / source.name
            if status == "ok":
                link_or_copy(cached, destination)
            audit.append({
                "image_id": row["image_id"],
                "relative_path": row["relative_path"],
                "fold": fold,
                "split": role,
                "variant": "predicted_roi",
                "status": status,
                "detection_stage": stage,
                "detector_confidence": confidence,
            })
        if index % 100 == 0 or index == len(rows):
            print(f"Processed {index}/{len(rows)} source images")

    output.mkdir(parents=True, exist_ok=True)
    with (output / "generation_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=audit[0])
        writer.writeheader()
        writer.writerows(audit)
    source_successes = sum(
        1 for row in audit
        if row["status"] == "ok" and (
            row["split"] in {"calibration", "test"} or
            (row["split"] == "validation" and int(row["fold"]) >= 0)
        )
    )
    # Every train-pool source appears exactly once as validation; calibration and
    # test appear once, so this count represents unique successful source images.
    print(f"Created classifier folds; successful source images: {source_successes}/{len(rows)}")
    print(f"Review detector failures in {output / 'generation_audit.csv'}")


if __name__ == "__main__":
    main()
