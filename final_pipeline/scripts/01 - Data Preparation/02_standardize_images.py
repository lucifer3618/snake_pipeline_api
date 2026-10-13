# Just normalize EXIF orientation and convert to RGB, then save as JPEG.
import argparse
import csv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from snake_pipeline.image_ops import load_rgb_standardized

# Set of allowed extentions
EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def main():
    # Parse arguments and validate input/output directories
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--quality", type=int, default=95)
    args = parser.parse_args()

    # Convert input/output strings to Path objects and initialize audit list
    source, output, audit = Path(args.input), Path(args.output), []

    # Iterate through all files in the input directory and process them
    for path in sorted(source.rglob("*")):
        # Only process files with allowed extensions
        if path.suffix.lower() not in EXTENSIONS: 
            continue
        # Determine the relative path of the file and the destination path in the output directory
        # Example: if input is "data/images" and file is "data/images/subdir/file.png", then relative will be "subdir/file.jpg"
        relative = path.relative_to(source).with_suffix(".jpg")
        destination = output / relative

        try:
            # Use the function from image_ops.py to load the image, 
            # normalize EXIF orientation, convert to RGB, and save as JPEG
            image = load_rgb_standardized(path)
            # Create the parent directories for the destination path if they don't exist
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Save the image as JPEG with the specified quality and no subsampling
            image.save(destination, "JPEG", quality=args.quality, subsampling=0)
            status = "ok"
        except Exception as error:
            status = f"failed:{error}"
        # Create the audit record for the file
        audit.append({"source": str(path), 
                      "output": str(destination),
                      "status": status})

    output.mkdir(parents=True, exist_ok=True)

    with (output / "standardization_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=audit[0].keys())
        writer.writeheader()
        writer.writerows(audit)

    print(f"Processed {len(audit)} files; originals were not resized or modified")


if __name__ == "__main__":
    main()

