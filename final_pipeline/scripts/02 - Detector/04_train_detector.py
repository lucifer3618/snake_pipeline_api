"""Train one YOLO11 instance-segmentation experiment.

This portable script preserves the original Ultralytics ``project/name``
output layout, including weights, args.yaml, results.csv and plots.
"""

import argparse
import os
import tempfile
from pathlib import Path

os.environ.setdefault("YOLO_CONFIG_DIR", tempfile.gettempdir())

from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train one YOLO segmentation model")
    parser.add_argument("--data-yaml", "--data_yaml", dest="data_yaml", required=True)
    parser.add_argument("--model-type", "--model_type", dest="model_type", required=True)
    parser.add_argument("--epochs", type=int, required=True)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--imgsz", type=int, required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--device", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_yaml = Path(args.data_yaml)
    if not data_yaml.is_file():
        raise FileNotFoundError(f"Dataset YAML not found: {data_yaml}")

    model = YOLO(args.model_type)

    print("---------------------------------------------")
    print("Training YOLO segmentation model")
    print(f"Model base : {args.model_type}")
    print(f"Dataset    : {data_yaml}")
    print(f"Epochs: {args.epochs} | Batch: {args.batch} | Imgsz: {args.imgsz}")
    print(f"Output     : {Path(args.project) / args.name}")
    print("---------------------------------------------")

    options = {
        "data": str(data_yaml), "epochs": args.epochs, "imgsz": args.imgsz,
        "batch": args.batch, "project": args.project, "name": args.name,
        "pretrained": True,
    }
    if args.device is not None:
        options["device"] = args.device

    result = model.train(**options)
    save_dir = Path(result.save_dir)
    print(f"Training complete. Results saved to: {save_dir}")


if __name__ == "__main__":
    main()
