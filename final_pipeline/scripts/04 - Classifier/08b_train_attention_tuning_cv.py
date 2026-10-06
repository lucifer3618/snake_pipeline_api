"""Tune SE/CBAM parameters while reusing the unchanged baseline training loop."""
import argparse
import csv
import importlib.util
import json
import sys
from copy import copy
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from snake_pipeline.models import build_model as shared_build_model


def load_baseline_trainer():
    path = Path(__file__).with_name("08_train_classifiers_cv.py")
    spec = importlib.util.spec_from_file_location("baseline_classifier_trainer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parser():
    result = argparse.ArgumentParser(
        description="Predeclared five-fold grid search for MobileNetV2 SE and CBAM parameters."
    )
    result.add_argument("--data-root", required=True)
    result.add_argument("--output", required=True)
    result.add_argument("--reductions", nargs="+", type=int, default=[4, 8, 16, 32])
    result.add_argument("--cbam-kernels", nargs="+", type=int, default=[3, 7])
    result.add_argument("--folds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    result.add_argument("--epochs", type=int, default=25)
    result.add_argument("--batch", type=int, default=32)
    result.add_argument("--workers", type=int, default=4)
    result.add_argument("--image-size", type=int, default=224)
    result.add_argument("--lr", type=float, default=3e-4)
    result.add_argument("--scheduler", choices=["cosine", "none"], default="cosine")
    result.add_argument("--min-lr", type=float, default=1e-6)
    result.add_argument("--weight-decay", type=float, default=1e-4)
    result.add_argument("--dropout", type=float, default=.2)
    result.add_argument("--label-smoothing", type=float, default=0.0)
    result.add_argument("--image-augmentation", choices=["none", "basic", "autoaugment"], default="basic")
    result.add_argument("--batch-augmentation", choices=["none", "mixup", "cutmix", "random"], default="none")
    result.add_argument("--mix-alpha", type=float, default=.2)
    result.add_argument("--mix-probability", type=float, default=.25)
    result.add_argument("--patience", type=int, default=5)
    result.add_argument("--seed", type=int, default=42)
    result.add_argument("--freeze-backbone-epochs", type=int, default=2)
    result.add_argument("--tracker", choices=["tensorboard", "none"], default="tensorboard")
    result.add_argument("--pretrained", action="store_true")
    result.add_argument("--amp", action="store_true")
    result.add_argument("--overwrite", action="store_true")
    return result


def validate(args):
    if any(value <= 0 for value in args.reductions):
        raise SystemExit("All reduction ratios must be positive")
    if any(value <= 0 or value % 2 == 0 for value in args.cbam_kernels):
        raise SystemExit("Every CBAM kernel must be a positive odd number")
    if len(set(args.reductions)) != len(args.reductions) or len(set(args.cbam_kernels)) != len(args.cbam_kernels):
        raise SystemExit("Search values must not contain duplicates")


def main():
    args = parser().parse_args()
    validate(args)
    trainer = load_baseline_trainer()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    configurations = [("mobilenet_v2_se", reduction, 7) for reduction in args.reductions]
    configurations += [("mobilenet_v2_cbam", reduction, kernel)
                       for reduction in args.reductions for kernel in args.cbam_kernels]
    print(f"Device: {device}; {len(configurations)} configurations x {len(args.folds)} folds = "
          f"{len(configurations) * len(args.folds)} runs")
    results = []

    for architecture, reduction, kernel in configurations:
        config_id = f"{architecture}__r{reduction}" + (f"_k{kernel}" if architecture.endswith("_cbam") else "")
        config_output = Path(args.output) / config_id

        def tuned_builder(architecture_name, classes, pretrained=True, dropout=.2, head_type="linear",
                          arc_scale=64., arc_margin=.5, dual_head=None):
            return shared_build_model(architecture_name, classes, pretrained, dropout, head_type,
                                      arc_scale, arc_margin, dual_head, reduction, kernel)

        trainer.build_model = tuned_builder
        run_args = copy(args)
        run_args.output = str(config_output)
        run_args.loss = "ce"
        run_args.focal_gamma = 2.0
        run_args.focal_alpha = "balanced"
        run_args.focal_weight = 1.0
        run_args.arc_scale = 64.0
        run_args.arc_margin = .5
        run_args.venom_weight = .25
        run_args.dual_head = False

        for fold in args.folds:
            fold_dir = config_output / f"{architecture}__ce" / f"fold_{fold}"
            metrics_path = fold_dir / "validation_metrics.json"
            checkpoint_path = fold_dir / "best.pt"
            if metrics_path.exists() and checkpoint_path.exists() and not args.overwrite:
                print(f"Skipping completed {config_id}, fold {fold}")
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            else:
                print(f"\nRunning {config_id}, fold {fold}", flush=True)
                metrics = trainer.train_one(architecture, fold, run_args, device)

            checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
            checkpoint.update({"attention_reduction": reduction, "cbam_kernel": kernel,
                               "attention_config": config_id})
            torch.save(checkpoint, checkpoint_path)
            metrics.update({"attention_reduction": reduction,
                            "cbam_kernel": kernel if architecture.endswith("_cbam") else None,
                            "attention_config": config_id})
            metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            results.append(metrics)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    fold_summary = output / "attention_fold_results.csv"
    with fold_summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader(); writer.writerows(results)

    ranked = []
    for config_id in sorted({row["attention_config"] for row in results}):
        selected = [row for row in results if row["attention_config"] == config_id]
        scores = np.asarray([row["macro_f1"] for row in selected], dtype=float)
        ranked.append({"attention_config": config_id, "architecture": selected[0]["architecture"],
                       "attention_reduction": selected[0]["attention_reduction"],
                       "cbam_kernel": selected[0]["cbam_kernel"], "completed_folds": len(scores),
                       "mean_macro_f1": scores.mean(),
                       "std_macro_f1": scores.std(ddof=1) if len(scores) > 1 else 0.0})
    ranked.sort(key=lambda row: (-row["mean_macro_f1"], row["attention_config"]))
    ranked_summary = output / "attention_tuning_summary.csv"
    with ranked_summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ranked[0].keys())
        writer.writeheader(); writer.writerows(ranked)
    print(f"\nRanked results saved to {ranked_summary}")
    for row in ranked:
        print(f"{row['attention_config']}: {row['mean_macro_f1']:.4f} +/- {row['std_macro_f1']:.4f}")


if __name__ == "__main__":
    main()
