"""Save visual predictions from a trained YOLO checkpoint."""

import argparse
import os
import tempfile
from pathlib import Path

os.environ.setdefault("YOLO_CONFIG_DIR", tempfile.gettempdir())

from ultralytics import YOLO


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize YOLO segmentation predictions")
    parser.add_argument("--source", required=True)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--output-dir", "--output_dir", dest="output_dir", required=True)
    parser.add_argument("--imgsz", type=int, default=None)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    weights = Path(args.weights)
    if not weights.is_file():
        raise FileNotFoundError(f"Weights file not found: {weights}")
    output = Path(args.output_dir)
    options = {
        "source": args.source, "save": True, "project": str(output.parent),
        "name": output.name, "exist_ok": True, "conf": args.conf,
        "retina_masks": True,
    }
    if args.imgsz is not None:
        options["imgsz"] = args.imgsz
    if args.device is not None:
        options["device"] = args.device
    results = YOLO(str(weights)).predict(**options)
    print(f"Processed {len(results)} item(s). Saved to: {output}")


if __name__ == "__main__":
    main()
