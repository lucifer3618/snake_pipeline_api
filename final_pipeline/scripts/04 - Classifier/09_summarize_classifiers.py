import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
import numpy as np


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--runs", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--loss", choices=["ce", "ce_focal", "arcface", "arcface_focal"])
    parser.add_argument("--architecture")
    parser.add_argument("--require-folds", type=int, default=5)
    parser.add_argument("--selection-output", help="Optional JSON record of the winning configuration")
    args = parser.parse_args()
    grouped = defaultdict(list)
    for path in Path(args.runs).glob("*/fold_*/validation_metrics.json"):
        metric = json.loads(path.read_text(encoding="utf-8"))
        if args.loss and metric.get("loss") != args.loss: continue
        if args.architecture and metric.get("architecture") != args.architecture: continue
        grouped[metric.get("experiment", metric["architecture"])].append(metric)
    rows = []
    for experiment, metrics in grouped.items():
        fold_ids = {int(metric["fold"]) for metric in metrics}
        if len(fold_ids) != len(metrics): raise SystemExit(f"Duplicate fold metrics found for {experiment}")
        if len(metrics) != args.require_folds:
            raise SystemExit(f"{experiment} has {len(metrics)} folds; expected {args.require_folds}")
        row = {"experiment": experiment, "architecture": metrics[0]["architecture"], "loss": metrics[0].get("loss","ce"), "folds": len(metrics)}
        for key in ("accuracy", "macro_precision", "macro_recall", "macro_f1"):
            values = [m[key] for m in metrics]; row[f"{key}_mean"] = np.mean(values); row[f"{key}_std"] = np.std(values, ddof=1)
        rows.append(row)
    rows.sort(key=lambda row: row["macro_f1_mean"], reverse=True)
    if not rows: raise SystemExit("No matching completed experiments found")
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
    print(f"Best classifier: {rows[0]['experiment']} macro F1={rows[0]['macro_f1_mean']:.4f}")
    if args.selection_output:
        selection = Path(args.selection_output); selection.parent.mkdir(parents=True, exist_ok=True)
        selection.write_text(json.dumps(rows[0], indent=2), encoding="utf-8")


if __name__ == "__main__": main()
