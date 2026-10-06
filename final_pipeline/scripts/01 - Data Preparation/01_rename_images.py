"""Copy class-folder images to clean folder_name_0001.ext names without altering originals."""
import argparse
import csv
import hashlib
import re
import shutil
from pathlib import Path

EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def slug(value): return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def sha256(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024): value.update(chunk)
    return value.hexdigest()


def main():
    # Parse arguments and validate input/output directories
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to input directory containing class folders with images")
    parser.add_argument("--output", required=True, help="Path to output directory where renamed images will be stored")
    parser.add_argument("--group-regex", help="Optional regex extracting animal/video/source ID from original filename")
    args = parser.parse_args()
    source, output = Path(args.input), Path(args.output)

    if source.resolve() == output.resolve():
        raise SystemExit("Input and output must differ")

    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Output must be empty: {output}. Choose a new directory to avoid mixed or duplicate files.")
    
    total = 0; audit = []

    for folder in sorted(path for path in source.iterdir() if path.is_dir()):

        name = slug(folder.name); images = sorted(path for path in folder.rglob("*") if path.suffix.lower() in EXTENSIONS)

        for index, image in enumerate(images, 1):
            destination = output / name / f"{name}_{index:04d}{image.suffix.lower()}"
            destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(image, destination); total += 1
            content_hash = sha256(image)

            match = re.search(args.group_regex, image.stem) if args.group_regex else None
            if args.group_regex and not match: raise SystemExit(f"Group regex did not match {image.name}")

            # A source/animal ID is strongest. Without one, the hash at least keeps
            # exact duplicate images together when data are split.
            group = (match.group(1) if match.groups() else match.group(0)) if match else f"sha256:{content_hash}"

            audit.append({"original_relative_path": image.relative_to(source).as_posix(),
                          "renamed_relative_path": destination.relative_to(output).as_posix(),
                          "group_id": group, "sha256": content_hash})
            
        print(f"{folder.name}: {len(images)}")

    with (output / "rename_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=audit[0]); writer.writeheader(); writer.writerows(audit)

    print(f"Copied and renamed {total} images to {output}")


if __name__ == "__main__": 
    main()
