"""Evaluate one trained YOLO instance-segmentation checkpoint."""

import argparse
import csv
import os
import tempfile
from pathlib import Path

os.environ.setdefault("YOLO_CONFIG_DIR", tempfile.gettempdir())

from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a YOLO segmentation checkpoint")
    parser.add_argument("--data-yaml", "--data_yaml", dest="data_yaml", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--split", choices=("train", "val", "test"), default="val")
    parser.add_argument("--imgsz", type=int, default=None)
    parser.add_argument("--batch", type=int, default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--experiment", default=None)
    parser.add_argument("--output", default=None, help="Optional CSV file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_yaml, weights = Path(args.data_yaml), Path(args.weights)
    if not data_yaml.is_file():
        raise FileNotFoundError(f"Dataset YAML not found: {data_yaml}")
    if not weights.is_file():
        raise FileNotFoundError(f"Weights file not found: {weights}")

    options = {
        "data": str(data_yaml), "split": args.split, "save": False,
        "save_txt": False, "save_json": False, "plots": False,
    }
    if args.imgsz is not None:
        options["imgsz"] = args.imgsz
    if args.batch is not None:
        options["batch"] = args.batch
    if args.device is not None:
        options["device"] = args.device

    result = YOLO(str(weights)).val(**options)
    row = {
        "experiment": args.experiment or weights.parents[1].name,
        "split": args.split,
        "box_precision": float(result.box.mp), "box_recall": float(result.box.mr),
        "box_map50": float(result.box.map50), "box_map50_95": float(result.box.map),
        "mask_precision": float(result.seg.mp), "mask_recall": float(result.seg.mr),
        "mask_map50": float(result.seg.map50), "mask_map50_95": float(result.seg.map),
        "preprocess_ms": float(result.speed.get("preprocess", 0.0)),
        "inference_ms": float(result.speed.get("inference", 0.0)),
        "postprocess_ms": float(result.speed.get("postprocess", 0.0)),
        "weights": str(weights.resolve()),
    }
    print(f"Mask precision : {row['mask_precision']:.4f}")
    print(f"Mask recall    : {row['mask_recall']:.4f}")
    print(f"Mask mAP50     : {row['mask_map50']:.4f}")
    print(f"Mask mAP50-95  : {row['mask_map50_95']:.4f}")

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        write_header = not output.exists() or output.stat().st_size == 0
        with output.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=row.keys())
            if write_header:
                writer.writeheader()
            writer.writerow(row)
        print(f"Metrics appended to: {output}")


if __name__ == "__main__":
    main()
