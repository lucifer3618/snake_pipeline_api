"""Measure fallback recovery on train-pool failures without using calibration/test."""

import argparse
import csv
import os
import tempfile
from pathlib import Path

os.environ.setdefault("YOLO_CONFIG_DIR", tempfile.gettempdir())

from ultralytics import YOLO


def has_mask(result) -> bool:
    return bool(result and result[0].masks is not None and result[0].boxes is not None and len(result[0].boxes))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True)
    parser.add_argument("--images", required=True)
    parser.add_argument("--primary", required=True)
    parser.add_argument("--secondary")
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", default="0")
    parser.add_argument("--retry-imgsz", type=int, default=768)
    parser.add_argument("--retry-conf", type=float, default=0.10)
    args = parser.parse_args()

    with open(args.audit, newline="", encoding="utf-8") as handle:
        audit = list(csv.DictReader(handle))
    grouped = {}
    for row in audit:
        grouped.setdefault(row["image_id"], []).append(row)
    failures = []
    for rows in grouped.values():
        roles = {row["split"] for row in rows}
        if roles & {"calibration", "test"} or rows[0]["status"] == "ok":
            continue
        failures.append(rows[0])

    primary = YOLO(args.primary)
    secondary = YOLO(args.secondary) if args.secondary else None
    output_rows = []
    for index, row in enumerate(failures, 1):
        image = Path(args.images) / Path(row["relative_path"])
        first = primary.predict(str(image), imgsz=args.retry_imgsz, conf=args.retry_conf,
                                device=args.device, retina_masks=True, verbose=False)
        recovered_by = "primary_retry" if has_mask(first) else ""
        confidence = float(first[0].boxes.conf.max()) if recovered_by else ""
        if not recovered_by and secondary is not None:
            second = secondary.predict(str(image), imgsz=args.retry_imgsz, conf=args.retry_conf,
                                       device=args.device, retina_masks=True, verbose=False)
            if has_mask(second):
                recovered_by = "secondary_retry"
                confidence = float(second[0].boxes.conf.max())
        output_rows.append({
            "image_id": row["image_id"], "relative_path": row["relative_path"],
            "recovered": bool(recovered_by), "recovered_by": recovered_by or "none",
            "confidence": confidence,
        })
        if index % 20 == 0 or index == len(failures):
            print(f"Probed {index}/{len(failures)}")

    if not output_rows:
        print("No eligible train-pool failures were found in the audit")
        return
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_rows[0])
        writer.writeheader()
        writer.writerows(output_rows)
    first_count = sum(row["recovered_by"] == "primary_retry" for row in output_rows)
    second_count = sum(row["recovered_by"] == "secondary_retry" for row in output_rows)
    print(f"Train-pool failures: {len(output_rows)}")
    print(f"Primary retry recovered: {first_count}")
    print(f"Secondary retry additionally recovered: {second_count}")
    print(f"Still missed: {len(output_rows) - first_count - second_count}")


if __name__ == "__main__":
    main()
