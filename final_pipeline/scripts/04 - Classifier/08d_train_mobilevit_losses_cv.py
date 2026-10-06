"""Run the four dual-head MobileViT loss ablations with the shared CV loop."""
import argparse
import csv
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from snake_pipeline.mobilevit import (MOBILEVIT_MODELS, build_mobilevit,
                                      mobilevit_loaders, resolve_preprocessing)

LOSSES = ("ce", "ce_focal", "arcface", "arcface_focal")


def load_baseline_trainer():
    path = Path(__file__).with_name("08_train_classifiers_cv.py")
    spec = importlib.util.spec_from_file_location("baseline_classifier_trainer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def argument_parser():
    parser = argparse.ArgumentParser(
        description="Five-fold CE/Focal/ArcFace ablation for dual-head MobileViT (FP32)."
    )
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", choices=MOBILEVIT_MODELS, default="mobilevit_xs.cvnets_in1k")
    parser.add_argument("--preprocessing", choices=["model", "shared"], default="model")
    parser.add_argument("--losses", nargs="+", choices=LOSSES, default=list(LOSSES))
    parser.add_argument("--folds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--image-size", type=int)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--scheduler", choices=["cosine", "none"], default="cosine")
    parser.add_argument("--min-lr", type=float, default=1e-6)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--dropout", type=float, default=.2)
    parser.add_argument("--label-smoothing", type=float, default=0.0)
    parser.add_argument("--venom-weight", type=float, default=.25)
    parser.add_argument("--focal-gamma", type=float, default=2.0)
    parser.add_argument("--focal-alpha", default="balanced")
    parser.add_argument("--focal-weight", type=float, default=1.0)
    parser.add_argument("--arc-scale", type=float, default=64.0)
    parser.add_argument("--arc-margin", type=float, default=.5)
    parser.add_argument("--image-augmentation", choices=["none", "basic", "autoaugment"], default="basic")
    parser.add_argument("--batch-augmentation", choices=["none", "mixup", "cutmix", "random"], default="none")
    parser.add_argument("--mix-alpha", type=float, default=.2)
    parser.add_argument("--mix-probability", type=float, default=.25)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--freeze-backbone-epochs", type=int, default=2)
    parser.add_argument("--tracker", choices=["tensorboard", "none"], default="tensorboard")
    parser.add_argument("--pretrained", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def log_hparams(output, experiment, fold, args, metrics):
    if args.tracker != "tensorboard":
        return
    from torch.utils.tensorboard import SummaryWriter
    writer = SummaryWriter(str(output / "tensorboard_hparams" / experiment / f"fold_{fold}"))
    writer.add_hparams(
        {"architecture": args.model, "loss": args.loss, "dual_head": True,
         "preprocessing": args.preprocessing, "image_size": args.image_size,
         "interpolation": args.interpolation, "learning_rate": args.lr,
         "weight_decay": args.weight_decay, "dropout": args.dropout,
         "batch_size": args.batch, "venom_weight": args.venom_weight,
         "focal_gamma": args.focal_gamma, "focal_weight": args.focal_weight,
         "arc_scale": args.arc_scale, "arc_margin": args.arc_margin,
         "freeze_backbone_epochs": args.freeze_backbone_epochs},
        {"hparam/accuracy": metrics["accuracy"], "hparam/macro_precision": metrics["macro_precision"],
         "hparam/macro_recall": metrics["macro_recall"], "hparam/macro_f1": metrics["macro_f1"]},
        run_name=experiment + f"_fold_{fold}",
    )
    writer.close()


def main():
    args = argument_parser().parse_args()
    import timm
    args.timm_version = timm.__version__
    preprocessing = resolve_preprocessing(args.model, args.preprocessing, args.image_size)
    args.image_size = preprocessing["image_size"]
    args.mean = preprocessing["mean"]
    args.std = preprocessing["std"]
    args.interpolation = preprocessing["interpolation"]
    args.dual_head = True
    args.amp = False  # MobileViT AMP produced non-finite losses in the architecture experiment.

    trainer = load_baseline_trainer()
    trainer.build_model = lambda architecture, classes, pretrained=True, dropout=.2, head_type="linear", \
        arc_scale=64., arc_margin=.5, dual_head=None: build_mobilevit(
            args.model, classes, pretrained, dropout, head_type, arc_scale, arc_margin, True)
    trainer.loaders = lambda fold_dir, batch, workers, image_size, augmentation: mobilevit_loaders(
        fold_dir, batch, workers, image_size, augmentation, args.mean, args.std, args.interpolation)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    print(f"Device: {device}; FP32; model={args.model}; input={args.image_size}; mean={args.mean}; "
          f"std={args.std}; interpolation={args.interpolation}")

    for loss in args.losses:
        args.loss = loss
        experiment = f"{args.model}__dual__{loss}"
        for fold in args.folds:
            fold_dir = output / experiment / f"fold_{fold}"
            metrics_path = fold_dir / "validation_metrics.json"
            checkpoint_path = fold_dir / "best.pt"
            if metrics_path.exists() and checkpoint_path.exists() and not args.overwrite:
                print(f"Skipping completed {experiment}, fold {fold}")
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            else:
                print(f"\nRunning {experiment}, fold {fold}", flush=True)
                metrics = trainer.train_one(args.model, fold, args, device)
            if not all(math.isfinite(float(metrics[key])) for key in
                       ("accuracy", "macro_precision", "macro_recall", "macro_f1")):
                raise SystemExit(f"Non-finite validation metric in {experiment}, fold {fold}; run rejected")

            checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
            checkpoint.update({"model_family": "timm_mobilevit", "timm_model": args.model,
                               "timm_version": args.timm_version,
                               "preprocessing": args.preprocessing, "image_size": args.image_size,
                               "normalization_mean": args.mean, "normalization_std": args.std,
                               "interpolation": args.interpolation, "precision": "fp32"})
            torch.save(checkpoint, checkpoint_path)
            metrics.update({"model": args.model, "preprocessing": args.preprocessing,
                            "image_size": args.image_size, "interpolation": args.interpolation,
                            "precision": "fp32", "dual_head": True})
            metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
            log_hparams(output, experiment, fold, args, metrics)
            results.append(metrics)

    fold_summary = output / "mobilevit_loss_fold_results.csv"
    with fold_summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader(); writer.writerows(results)

    ranked = []
    for loss in args.losses:
        selected = [row for row in results if row["loss"] == loss]
        scores = np.asarray([row["macro_f1"] for row in selected], dtype=float)
        ranked.append({"loss": loss, "folds": len(scores), "macro_f1_mean": float(scores.mean()),
                       "macro_f1_std": float(scores.std(ddof=1)) if len(scores) > 1 else 0.0})
    ranked.sort(key=lambda row: (-row["macro_f1_mean"], row["loss"]))
    summary = output / "mobilevit_loss_summary.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ranked[0].keys())
        writer.writeheader(); writer.writerows(ranked)
    selection = {"architecture": args.model, "dual_head": True, **ranked[0]}
    (output / "selected_mobilevit_loss.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    print(f"\nWinning loss: {ranked[0]['loss']} macro F1={ranked[0]['macro_f1_mean']:.4f}")
    print(f"Saved {fold_summary}, {summary}, and selected_mobilevit_loss.json")


if __name__ == "__main__":
    main()
