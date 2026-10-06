"""Train MobileViT with the unchanged classifier CV loop and explicit preprocessing."""
import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import ImageFolder

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from snake_pipeline.config import SPECIES
from snake_pipeline.image_ops import PadToSquare


def load_baseline_trainer():
    path = Path(__file__).with_name("08_train_classifiers_cv.py")
    spec = importlib.util.spec_from_file_location("baseline_classifier_trainer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MobileViTClassifier(nn.Module):
    """Adapter exposing the interface expected by the shared training loop."""
    def __init__(self, model_name, classes, pretrained=True, dropout=.2):
        super().__init__()
        try:
            import timm
        except ImportError as error:
            raise SystemExit("MobileViT requires timm; run: pip install -r requirements.txt") from error
        backbone = timm.create_model(model_name, pretrained=pretrained, num_classes=0, global_pool="avg")
        self.features = nn.Sequential(backbone)
        self.dropout = nn.Dropout(dropout)
        self.species_head = nn.Linear(backbone.num_features, classes)
        self.venom_head = None
        self.dual_head = False

    def extract_features(self, images):
        return self.dropout(self.features(images))

    def classify_features(self, features, labels=None):
        return self.species_head(features)

    def forward(self, images, labels=None):
        return self.classify_features(self.extract_features(images), labels)


def transform(training, size, augmentation, mean, std, interpolation):
    interpolation_mode = getattr(transforms.InterpolationMode, interpolation.upper(),
                                 transforms.InterpolationMode.BICUBIC)
    operations = [PadToSquare(0), transforms.Resize((size, size), interpolation=interpolation_mode)]
    if training:
        if augmentation == "autoaugment":
            operations += [transforms.RandomHorizontalFlip(),
                           transforms.AutoAugment(transforms.AutoAugmentPolicy.IMAGENET)]
        elif augmentation == "basic":
            operations += [transforms.RandomHorizontalFlip(), transforms.RandomRotation(10),
                           transforms.ColorJitter(brightness=.15, contrast=.15, saturation=.10)]
        elif augmentation != "none":
            raise ValueError(f"Unknown augmentation policy: {augmentation}")
    operations += [transforms.ToTensor(), transforms.Normalize(mean, std)]
    return transforms.Compose(operations)


def mobilevit_loaders(fold_dir, batch, workers, image_size, augmentation, mean, std, interpolation):
    root = Path(fold_dir)
    datasets = {}
    for split in ("train", "validation", "calibration", "test"):
        if (root / split).is_dir():
            datasets[split] = ImageFolder(
                root / split,
                transform(split == "train", image_size, augmentation, mean, std, interpolation),
            )
            if datasets[split].classes != SPECIES:
                raise ValueError(f"Unexpected class folders in {root / split}: {datasets[split].classes}")
    if not {"train", "validation"}.issubset(datasets):
        raise ValueError("fold directory needs train/ and validation/")
    loaders = {name: DataLoader(dataset, batch_size=batch, shuffle=name == "train",
               num_workers=workers, pin_memory=torch.cuda.is_available(),
               persistent_workers=workers > 0) for name, dataset in datasets.items()}
    return loaders, datasets


def argument_parser():
    parser = argparse.ArgumentParser(description="Five-fold MobileViT CE architecture experiment")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="mobilevit_xs.cvnets_in1k",
                        choices=["mobilevit_xxs.cvnets_in1k", "mobilevit_xs.cvnets_in1k",
                                 "mobilevit_s.cvnets_in1k"])
    parser.add_argument("--preprocessing", choices=["model", "shared"], default="model")
    parser.add_argument("--folds", nargs="+", type=int, default=[0, 1, 2, 3, 4])
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--image-size", type=int)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--scheduler", choices=["cosine", "none"], default="cosine")
    parser.add_argument("--min-lr", type=float, default=1e-6)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--dropout", type=float, default=.2)
    parser.add_argument("--label-smoothing", type=float, default=0.0)
    parser.add_argument("--image-augmentation", choices=["none", "basic", "autoaugment"], default="basic")
    parser.add_argument("--batch-augmentation", choices=["none", "mixup", "cutmix", "random"], default="none")
    parser.add_argument("--mix-alpha", type=float, default=.2)
    parser.add_argument("--mix-probability", type=float, default=.25)
    parser.add_argument("--patience", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--freeze-backbone-epochs", type=int, default=2)
    parser.add_argument("--tracker", choices=["tensorboard", "none"], default="tensorboard")
    parser.add_argument("--pretrained", action="store_true")
    parser.add_argument("--amp", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def model_data_config(model_name):
    try:
        import timm
        from timm.data import resolve_model_data_config
    except ImportError as error:
        raise SystemExit("MobileViT requires timm; run: pip install -r requirements.txt") from error
    probe = timm.create_model(model_name, pretrained=False)
    return resolve_model_data_config(probe)


def log_hparams(output, experiment, fold, args, metrics):
    if args.tracker != "tensorboard":
        return
    from torch.utils.tensorboard import SummaryWriter
    writer = SummaryWriter(str(output / "tensorboard_hparams" / experiment / f"fold_{fold}"))
    writer.add_hparams(
        {"architecture": args.model, "preprocessing": args.preprocessing,
         "image_size": args.image_size, "interpolation": args.interpolation,
         "learning_rate": args.lr, "weight_decay": args.weight_decay,
         "dropout": args.dropout, "batch_size": args.batch,
         "freeze_backbone_epochs": args.freeze_backbone_epochs,
         "image_augmentation": args.image_augmentation,
         "batch_augmentation": args.batch_augmentation},
        {"hparam/accuracy": metrics["accuracy"], "hparam/macro_precision": metrics["macro_precision"],
         "hparam/macro_recall": metrics["macro_recall"], "hparam/macro_f1": metrics["macro_f1"]},
        run_name=experiment + f"_fold_{fold}",
    )
    writer.close()


def main():
    args = argument_parser().parse_args()
    trainer = load_baseline_trainer()
    config = model_data_config(args.model)
    if args.preprocessing == "model":
        args.image_size = args.image_size or int(config["input_size"][-1])
        args.mean = list(config["mean"])
        args.std = list(config["std"])
        args.interpolation = config.get("interpolation", "bicubic")
    else:
        args.image_size = args.image_size or 224
        args.mean = [.485, .456, .406]
        args.std = [.229, .224, .225]
        args.interpolation = "bilinear"

    # Fields required by the unchanged baseline train_one function.
    args.loss = "ce"
    args.focal_gamma = 2.0
    args.focal_alpha = "balanced"
    args.focal_weight = 1.0
    args.arc_scale = 64.0
    args.arc_margin = .5
    args.venom_weight = .25
    args.dual_head = False

    trainer.build_model = lambda architecture, classes, pretrained=True, dropout=.2, head_type="linear", \
        arc_scale=64., arc_margin=.5, dual_head=None: MobileViTClassifier(args.model, classes, pretrained, dropout)
    trainer.loaders = lambda fold_dir, batch, workers, image_size, augmentation: mobilevit_loaders(
        fold_dir, batch, workers, image_size, augmentation, args.mean, args.std, args.interpolation)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    experiment = f"{args.model.replace('.', '_')}__ce__prep_{args.preprocessing}"
    original_output = Path(args.output)
    run_output = original_output / experiment
    args.output = str(run_output)
    results = []
    print(f"Device: {device}; model={args.model}; input={args.image_size}; mean={args.mean}; "
          f"std={args.std}; interpolation={args.interpolation}")

    for fold in args.folds:
        internal_experiment = f"{args.model}__ce"
        fold_dir = run_output / internal_experiment / f"fold_{fold}"
        metrics_path = fold_dir / "validation_metrics.json"
        checkpoint_path = fold_dir / "best.pt"
        if metrics_path.exists() and checkpoint_path.exists() and not args.overwrite:
            print(f"Skipping completed {experiment}, fold {fold}")
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        else:
            metrics = trainer.train_one(args.model, fold, args, device)
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
        checkpoint.update({"model_family": "timm_mobilevit", "timm_model": args.model,
                           "preprocessing": args.preprocessing, "image_size": args.image_size,
                           "normalization_mean": args.mean, "normalization_std": args.std,
                           "interpolation": args.interpolation})
        torch.save(checkpoint, checkpoint_path)
        metrics.update({"model": args.model, "preprocessing": args.preprocessing,
                        "image_size": args.image_size, "interpolation": args.interpolation})
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        log_hparams(original_output, experiment, fold, args, metrics)
        results.append(metrics)

    fold_summary = original_output / f"{experiment}__fold_results.csv"
    with fold_summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader(); writer.writerows(results)
    scores = np.asarray([result["macro_f1"] for result in results], dtype=float)
    summary = {"experiment": experiment, "model": args.model, "preprocessing": args.preprocessing,
               "completed_folds": len(scores), "mean_macro_f1": float(scores.mean()),
               "std_macro_f1": float(scores.std(ddof=1)) if len(scores) > 1 else 0.0}
    summary_path = original_output / f"{experiment}__summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved {fold_summary} and {summary_path}")


if __name__ == "__main__":
    main()
