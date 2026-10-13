# Rename images in a directory structure while keepintg track of
# the original names and their new names in a CSV file. 
import argparse
import csv
import hashlib
import re
import shutil
from pathlib import Path

# Supported image file extensions
EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


# remove all non-alphanumeric characters and replace them with underscores 
# Ex:- Naja Naja -> naja_naja
def slug(value): 
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def sha256(path):
    # Create a SHA256 hash of the file content to identify duplicates
    value = hashlib.sha256()
    with path.open("rb") as handle:
        # Read the file in chunks to avoid memory issues with large files
        while chunk := handle.read(1024 * 1024): value.update(chunk)
    # Return the hexadecimal string of the hash
    return value.hexdigest()


def main():
    # Parse arguments and validate input/output directories
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to input directory containing class folders with images")
    parser.add_argument("--output", required=True, help="Path to output directory where renamed images will be stored")
    parser.add_argument("--group-regex", help="Optional regex extracting animal/video/source ID from original filename")
    args = parser.parse_args()

    # Convert input and output paths to Path objects for easier manipulation
    source, output = Path(args.input), Path(args.output)

    # Ensure that the input and output directories are not the same
    if source.resolve() == output.resolve():
        raise SystemExit("Input and output must differ")

    # Ensure that the output directory is empty
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Output must be empty: {output}. Choose a new directory to avoid mixed or duplicate files.")
    
    total = 0; audit = []

    # Iterate through each folder in the source directory
    for folder in sorted(path for path in source.iterdir() if path.is_dir()):

        # Create a slugified version of the folder name for consistent naming
        name = slug(folder.name);

        # Go over each image in the folder if the file extension is supported, sort them for consistent ordering
        images = sorted(path for path in folder.rglob("*") if path.suffix.lower() in EXTENSIONS)

        # Enumerate through the images. And index starts at one
        for index, image in enumerate(images, 1):
            # Create a destination path for the renamed image in the output directory.
            # 004d means 4 digits with leading zeros. Ex:- 0001, 0002, 0003
            destination = output / name / f"{name}_{index:04d}{image.suffix.lower()}"

            # Create a destination object for the parent directory of the destination path,
            # ensuring that it exists before copying the image.
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy the image to the destination path while preserving metadata
            shutil.copy2(image, destination)
            # Increment the total count of images processed
            total += 1
            # Generate a SHA256 hash of the image content to identify duplicates
            content_hash = sha256(image)

            match = re.search(args.group_regex, image.stem) if args.group_regex else None
            if args.group_regex and not match: 
                raise SystemExit(f"Group regex did not match {image.name}")

            # A source/animal ID is strongest. Without one, the hash at least keeps
            # exact duplicate images together when data are split.
            group = (match.group(1) if match.groups() else match.group(0)) if match else f"sha256:{content_hash}"

            audit.append({"original_relative_path": image.relative_to(source).as_posix(),
                          "renamed_relative_path": destination.relative_to(output).as_posix(),
                          "group_id": group,
                          "sha256": content_hash})
            
        print(f"{folder.name}: {len(images)}")

    with (output / "rename_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        # Write the audit information to a CSV file, including headers and rows for each image processed
        # Takes key as the first row of the audit list to determine the fieldnames for the CSV
        writer=csv.DictWriter(handle,fieldnames=audit[0])
        # Write the header row to the CSV file
        writer.writeheader()
        # Write the rows of audit information to the CSV file
        writer.writerows(audit)

    print(f"Copied and renamed {total} images to {output}")


if __name__ == "__main__": 
    main()
