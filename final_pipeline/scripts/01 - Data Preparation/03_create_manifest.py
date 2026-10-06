"""Create grouped train_pool/calibration/test partitions and stratified CV folds."""
import argparse
import csv
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def extracted_group(path, pattern):
    if not pattern: return path.stem
    match = re.search(pattern, path.stem)
    if not match: raise ValueError(f"Group regex did not match {path.name}")
    return match.group(1) if match.groups() else match.group(0)


def allocate(groups, fraction, rng):
    items = list(groups.items()); rng.shuffle(items); target = round(sum(len(rows) for _, rows in items) * fraction)
    selected, count = [], 0
    for group, rows in items:
        if count >= target: break
        selected.append(group); count += len(rows)
    return set(selected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--test-ratio", type=float, default=.10); parser.add_argument("--calibration-ratio", type=float, default=.10)
    parser.add_argument("--folds", type=int, default=5); parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--group-regex", help="Extract actual animal/video/source ID; never use species name")
    parser.add_argument("--rename-manifest", help="Optional manifest from 01_rename_images.py preserving original source groups")
    args = parser.parse_args()

    root, rng = Path(args.images), random.Random(args.seed)

    rows = []
    saved_groups = {}

    if args.rename_manifest:
        with open(args.rename_manifest, newline="", encoding="utf-8") as handle:
            saved_groups = {Path(row["renamed_relative_path"]).with_suffix(".jpg").as_posix(): row["group_id"] for row in csv.DictReader(handle)}
            
    for class_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        for path in sorted(class_dir.rglob("*")):
            if path.suffix.lower() in EXTENSIONS:
                relative = path.relative_to(root).as_posix()
                group = saved_groups[relative] if relative in saved_groups else extracted_group(path, args.group_regex)
                rows.append({"image_id": path.stem, "relative_path": relative,
                    "class_name": class_dir.name.lower(), "group_id": group, "split": "", "fold": ""})
    by_class = defaultdict(lambda: defaultdict(list))
    for row in rows: by_class[row["class_name"]][row["group_id"]].append(row)
    for class_name, groups in by_class.items():
        if len(groups) < args.folds + 2: raise SystemExit(f"{class_name} has only {len(groups)} groups; check grouping")
        test = allocate(groups, args.test_ratio, rng); remaining = {k:v for k,v in groups.items() if k not in test}
        calibration = allocate(remaining, args.calibration_ratio / (1-args.test_ratio), rng)
        fold_sizes = [0] * args.folds; pool_groups = [(k,v) for k,v in remaining.items() if k not in calibration]
        rng.shuffle(pool_groups); pool_groups.sort(key=lambda item: len(item[1]), reverse=True)
        for group, group_rows in groups.items():
            split = "test" if group in test else "calibration" if group in calibration else "train_pool"
            for row in group_rows: row["split"] = split
        for _, group_rows in pool_groups:
            fold = min(range(args.folds), key=lambda value: (fold_sizes[value], value))
            for row in group_rows: row["fold"] = fold
            fold_sizes[fold] += len(group_rows)
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {output}: {dict(Counter(r['split'] for r in rows))}")


if __name__ == "__main__": main()
