"""Build whole-image classifier folds from the existing split manifest."""
import argparse
import csv
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from snake_pipeline.config import SPECIES


def link_or_copy(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        shutil.copy2(source, destination)
        return "copy"


def roles_for(row: dict, folds: list[int]):
    if row["split"] == "train_pool":
        held_out = int(row["fold"])
        for fold in folds:
            yield fold, "validation" if fold == held_out else "train"
    elif row["split"] in {"calibration", "test"}:
        yield 0, row["split"]
    else:
        raise ValueError(f"Unknown split for {row['image_id']}: {row['split']}")


def successful_predicted_roi_ids(audit_path: Path) -> set[str]:
    with audit_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"image_id", "variant", "status"}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit(f"Audit must contain {sorted(required)}: {audit_path}")
    return {row["image_id"] for row in rows
            if row["variant"] == "predicted_roi" and row["status"] == "ok"}


def main():
    parser = argparse.ArgumentParser(
        description="Create manifest-controlled whole-image folds without modifying standardized images."
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--images", required=True, help="Standardized class-folder root")
    parser.add_argument("--output", required=True, help="New empty fold root")
    parser.add_argument("--population", choices=["matched", "all"], default="matched",
                        help="matched uses only successful predicted-ROI image IDs")
    parser.add_argument("--audit", help="Classifier generation_audit.csv; required for matched population")
    args = parser.parse_args()

    manifest_path, image_root, output = Path(args.manifest), Path(args.images), Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"Output must be empty: {output}")
    if args.population == "matched" and not args.audit:
        raise SystemExit("--population matched requires --audit generation_audit.csv")

    with manifest_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    required = {"image_id", "relative_path", "class_name", "split", "fold"}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit(f"Manifest must contain {sorted(required)}: {manifest_path}")
    image_ids = [row["image_id"] for row in rows]
    if len(set(image_ids)) != len(image_ids):
        raise SystemExit("Manifest contains duplicate image_id values")
    classes = sorted({row["class_name"] for row in rows})
    if classes != SPECIES:
        raise SystemExit(f"Manifest species do not match configured species: {classes}")
    folds = sorted({int(row["fold"]) for row in rows if row["split"] == "train_pool"})
    if folds != [0, 1, 2, 3, 4]:
        raise SystemExit(f"Expected train-pool folds 0-4, found {folds}")

    eligible = (successful_predicted_roi_ids(Path(args.audit))
                if args.population == "matched" else set(image_ids))
    selected = [row for row in rows if row["image_id"] in eligible]
    if not selected:
        raise SystemExit("No manifest images matched the requested population")
    unknown = eligible.difference(image_ids)
    if unknown:
        print(f"Warning: audit contains {len(unknown)} image IDs absent from the manifest")

    resolved = []
    missing = []
    for row in selected:
        relative = Path(row["relative_path"].replace("\\", "/"))
        source = image_root / relative
        if not source.is_file():
            missing.append(str(source))
        resolved.append((row, source))
    if missing:
        preview = "\n".join(missing[:10])
        raise SystemExit(f"Missing {len(missing)} standardized images; first paths:\n{preview}")

    output.mkdir(parents=True, exist_ok=True)
    audit_rows = []
    methods = Counter()
    for row, source in resolved:
        for fold, role in roles_for(row, folds):
            destination = output / f"fold_{fold}" / role / row["class_name"] / source.name
            method = link_or_copy(source, destination)
            methods[method] += 1
            audit_rows.append({"image_id": row["image_id"], "relative_path": row["relative_path"],
                               "class_name": row["class_name"], "source_split": row["split"],
                               "source_fold": row["fold"], "fold": fold, "role": role,
                               "method": method, "destination": str(destination.relative_to(output))})

    with (output / "whole_image_fold_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=audit_rows[0].keys())
        writer.writeheader(); writer.writerows(audit_rows)
    unique_by_split = Counter(row["split"] for row in selected)
    summary = {"population": args.population, "manifest_images": len(rows),
               "selected_unique_images": len(selected), "excluded_unique_images": len(rows) - len(selected),
               "selected_by_source_split": dict(unique_by_split), "fold_entries": len(audit_rows),
               "storage_methods": dict(methods)}
    import json
    (output / "whole_image_fold_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Whole-image folds created at {output}")


if __name__ == "__main__":
    main()
