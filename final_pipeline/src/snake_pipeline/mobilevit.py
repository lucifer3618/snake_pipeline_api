"""MobileViT model adapter and checkpoint-specific data utilities."""
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder

from .config import SPECIES
from .image_ops import classifier_transform
from .losses import ArcMarginProduct

MOBILEVIT_MODELS = ("mobilevit_xxs.cvnets_in1k", "mobilevit_xs.cvnets_in1k", "mobilevit_s.cvnets_in1k")


def _timm():
    try:
        import timm
        return timm
    except ImportError as error:
        raise RuntimeError("MobileViT requires timm; run: pip install -r requirements.txt") from error


class MobileViTClassifier(nn.Module):
    def __init__(self, model_name, classes, pretrained=True, dropout=.2, head_type="linear",
                 arc_scale=64., arc_margin=.5, dual_head=False):
        super().__init__()
        if model_name not in MOBILEVIT_MODELS:
            raise ValueError(f"Unknown MobileViT model: {model_name}")
        backbone = _timm().create_model(model_name, pretrained=pretrained, num_classes=0, global_pool="avg")
        width = backbone.num_features
        self.model_name = model_name
        self.features = nn.Sequential(backbone)
        self.dropout = nn.Dropout(dropout)
        self.head_type = head_type
        self.dual_head = bool(dual_head)
        self.species_head = (ArcMarginProduct(width, classes, arc_scale, arc_margin)
                             if head_type == "arcface" else nn.Linear(width, classes))
        self.venom_head = nn.Linear(width, 2) if self.dual_head else None

    def extract_features(self, images):
        return self.dropout(self.features(images))

    def classify_features(self, features, labels=None):
        return self.species_head(features, labels) if self.head_type == "arcface" else self.species_head(features)

    def forward(self, images, labels=None):
        features = self.extract_features(images)
        species = self.classify_features(features, labels)
        return (species, self.venom_head(features)) if self.dual_head else species


def build_mobilevit(model_name, classes, pretrained=True, dropout=.2, head_type="linear",
                    arc_scale=64., arc_margin=.5, dual_head=False):
    return MobileViTClassifier(model_name, classes, pretrained, dropout, head_type,
                               arc_scale, arc_margin, dual_head)


def resolve_preprocessing(model_name, mode="model", image_size=None):
    if mode == "shared":
        return {"image_size": image_size or 224, "mean": [.485, .456, .406],
                "std": [.229, .224, .225], "interpolation": "bilinear"}
    if mode != "model":
        raise ValueError(f"Unknown preprocessing mode: {mode}")
    from timm.data import resolve_model_data_config
    config = resolve_model_data_config(_timm().create_model(model_name, pretrained=False))
    return {"image_size": image_size or int(config["input_size"][-1]),
            "mean": list(config["mean"]), "std": list(config["std"]),
            "interpolation": config.get("interpolation", "bicubic")}


def mobilevit_loaders(fold_dir, batch, workers, image_size, augmentation, mean, std, interpolation):
    root = Path(fold_dir)
    datasets = {}
    for split in ("train", "validation", "calibration", "test"):
        if (root / split).is_dir():
            datasets[split] = ImageFolder(
                root / split,
                classifier_transform(split == "train", image_size, augmentation, mean, std, interpolation),
            )
            if datasets[split].classes != SPECIES:
                raise ValueError(f"Unexpected class folders in {root / split}: {datasets[split].classes}")
    if not {"train", "validation"}.issubset(datasets):
        raise ValueError("fold directory needs train/ and validation/")
    result = {name: DataLoader(dataset, batch_size=batch, shuffle=name == "train", num_workers=workers,
              pin_memory=torch.cuda.is_available(), persistent_workers=workers > 0)
              for name, dataset in datasets.items()}
    return result, datasets
