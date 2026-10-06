from pathlib import Path
import torch
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
from .config import SPECIES
from .image_ops import classifier_transform


def loaders(fold_dir, batch=32, workers=4, image_size=224, augmentation="basic"):
    root = Path(fold_dir); datasets = {}
    for split in ("train", "validation", "calibration", "test"):
        if (root / split).is_dir():
            datasets[split] = ImageFolder(root / split, classifier_transform(split == "train", image_size, augmentation))
            if datasets[split].classes != SPECIES: raise ValueError(f"Unexpected class folders in {root/split}: {datasets[split].classes}")
    if not {"train", "validation"}.issubset(datasets): raise ValueError("fold directory needs train/ and validation/")
    result = {name: DataLoader(ds, batch_size=batch, shuffle=name == "train", num_workers=workers,
              pin_memory=torch.cuda.is_available(), persistent_workers=workers > 0) for name, ds in datasets.items()}
    return result, datasets
