# Create a manifest CSV file for a dataset of images, including train, test, and calibration splits,
# as well as fold assignments for cross-validation.
import argparse
import csv
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

# Set of allowed extensions
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# Determine the group ID for a given image path based on the provided regex pattern
def extracted_group(path, pattern):
    # If no pattern is provided, return the stem of the path (filename without extension)
    # Ex: If the path is "images/cat/123.jpg" and no pattern is provided, it will return "123"
    if not pattern:
        return path.stem
    # Match the provided regex pattern against the stem of the path
    # snake_	Matches the literal text snake_
    # \d	    Matches a digit
    # +	Matches one or more digits
    # (\d+)	    Captures those digits as a group
    match = re.search(pattern, path.stem)
    if not match:
        raise ValueError(f"Group regex did not match {path.name}")
    # if the regex has capturing groups, return the first captured group; otherwise, return the entire match
    return match.group(1) if match.groups() else match.group(0)


def allocate(groups, fraction, rng):
    items = list(groups.items())
    rng.shuffle(items)
    target = round(sum(len(rows) for _, rows in items) * fraction)
    selected, count = [], 0
    for group, rows in items:
        if count >= target: break
        selected.append(group); count += len(rows)
    return set(selected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--test-ratio", type=float, default=.10)
    parser.add_argument("--calibration-ratio", type=float, default=.10)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--group-regex", help="Extract actual animal/video/source ID; never use species name")
    parser.add_argument("--rename-manifest", help="Optional manifest from 01_rename_images.py preserving original source groups")
    args = parser.parse_args()

    # Convert to Path and Random objects
    root, rng = Path(args.images), random.Random(args.seed)

    rows = []
    saved_groups = {}

    # If a exsiting rename manifest is provided, read it and store the group IDs for each renamed image
    if args.rename_manifest:
        with open(args.rename_manifest, newline="", encoding="utf-8") as handle:
            saved_groups = {
                Path(row["renamed_relative_path"]).with_suffix(".jpg").as_posix(): row["group_id"] 
                for row in csv.DictReader(handle)
                }

    # Go over each class directory inside the main dataset directory
    for class_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        # Go over each items in selected class directory and its subdirectories
        for path in sorted(class_dir.rglob("*")):
            # check if the file has an allowed image extension
            if path.suffix.lower() in EXTENSIONS:
                # Determine the relative path of the image with respect to the root directory and convert it to a POSIX-style string
                # Ex: If the root is "data" and the image path is "data/naja_naja/naja_naja_0001.jpg",
                # the relative path will be "naja_naja/naja_naja_0001.jpg"
                relative = path.relative_to(root).as_posix()

                # This approch used provided regex to extract group ID from the image filename.
                # If a rename manifest is provided, it will use the group ID from that manifest instead.
                group = saved_groups[relative] if relative in saved_groups else extracted_group(path, args.group_regex)
                # create a dictionary for each image containing its metadata and append it to the rows list
                rows.append({"image_id": path.stem, 
                             "relative_path": relative,
                             "class_name": class_dir.name.lower(),
                             "group_id": group,
                             "split": "",
                             "fold": ""})
                
    by_class = defaultdict(lambda: defaultdict(list))

    for row in rows:
        by_class[row["class_name"]][row["group_id"]].append(row)
    # {
    #     "naja_naja": {
    #         "123": [image1, image2],
    #         "124": [image3]
    #     },
    #     "daboia_russelii": {
    #         "201": [image4, image5],
    #         "202": [image6]
    #     }
    # }


    # Go over each class and its groups to allocate them into test, calibration, and train_pool splits
    # In my case because i use hash most of the images are in their own group
    for class_name, groups in by_class.items():
        # Because we need adddtional clibration split, we need at least folds + 2 groups for each class
        if len(groups) < args.folds + 2: 
            raise SystemExit(f"{class_name} has only {len(groups)} groups; check grouping")

        # From groups randomly allocate given ratio of groups to test and calibration splits, the rest will be used for training
        test = allocate(groups, args.test_ratio, rng)
        remaining = {k:v for k,v in groups.items() if k not in test}
        calibration = allocate(remaining, args.calibration_ratio / (1-args.test_ratio), rng)

        # List to keep track of the number of images in each fold for stratified allocation
        fold_sizes = [0] * args.folds

        pool_groups = [(k,v) for k,v in remaining.items() if k not in calibration]

        # Randomly shuffle the pool groups to ensure randomness in fold allocation
        rng.shuffle(pool_groups)
        # Sort the pool groups in descending order based on the number of images in each group. 
        pool_groups.sort(key=lambda item: len(item[1]), reverse=True)
        # 
        for group, group_rows in groups.items():
            split = "test" if group in test else "calibration" if group in calibration else "train_pool"
            for row in group_rows:
                row["split"] = split
        for _, group_rows in pool_groups:
            fold = min(range(args.folds), key=lambda value: (fold_sizes[value], value))
            for row in group_rows: 
                row["fold"] = fold
            fold_sizes[fold] += len(group_rows)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output}: {dict(Counter(r['split'] for r in rows))}")


if __name__ == "__main__":
    main()
