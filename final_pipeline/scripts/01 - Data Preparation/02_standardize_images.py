"""Normalize EXIF orientation, color mode and format without resizing or padding."""
import argparse
import csv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from snake_pipeline.image_ops import load_rgb_standardized

EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def main():
    # Parse arguments and validate input/output directories
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--quality", type=int, default=95); args = parser.parse_args()

    source, output, audit = Path(args.input), Path(args.output), []

    for path in sorted(source.rglob("*")):
        if path.suffix.lower() not in EXTENSIONS: continue
        relative = path.relative_to(source).with_suffix(".jpg"); destination = output / relative

        try:
            image = load_rgb_standardized(path); destination.parent.mkdir(parents=True, exist_ok=True)
            image.save(destination, "JPEG", quality=args.quality, subsampling=0); status = "ok"
        except Exception as error: status = f"failed:{error}"
        audit.append({"source": str(path), "output": str(destination), "status": status})

    output.mkdir(parents=True, exist_ok=True)

    with (output / "standardization_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=audit[0].keys()); writer.writeheader(); writer.writerows(audit)

    print(f"Processed {len(audit)} files; originals were not resized or modified")


if __name__ == "__main__": main()
