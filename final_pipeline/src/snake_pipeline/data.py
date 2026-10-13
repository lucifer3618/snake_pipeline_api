from pathlib import Path
import torch
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
from .config import SPECIES
from .image_ops import classifier_transform


def loaders(fold_dir, batch=32, workers=4, image_size=224, augmentation="basic"):
    root = Path(fold_dir)
    datasets = {}
    for split in ("train", "validation", "calibration", "test"):
        if (root / split).is_dir():
            datasets[split] = ImageFolder(
                root / split,
                # The classifier_transform function is used to apply a series of transformations to the images in the dataset.
                classifier_transform(split == "train", image_size, augmentation)
            )

            if datasets[split].classes != SPECIES:
                raise ValueError(f"Unexpected class folders in {root/split}: {datasets[split].classes}")
            
    if not {"train", "validation"}.issubset(datasets):
        raise ValueError("fold directory needs train/ and validation/")
    
    result = {
        # The DataLoader is a PyTorch utility that provides an iterable over the dataset,
        # allowing for efficient batching and shuffling of data during training and evaluation.
        name: DataLoader(
            ds,
            # The batch_size parameter specifies the number of samples to be loaded in each batch.
            batch_size=batch,
            shuffle=name == "train",
            # The num_workers parameter specifies the number of subprocesses to use for data loading.
            num_workers=workers,
            pin_memory=torch.cuda.is_available(),
            persistent_workers=workers > 0) for name, ds in datasets.items()
        }
    return result, datasets
