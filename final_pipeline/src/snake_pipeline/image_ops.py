from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
from torchvision import transforms
from torchvision.transforms import functional as TF


class PadToSquare:
    def __init__(self, fill=0): self.fill = fill
    def __call__(self, image):
        width, height = image.size; size = max(width, height)
        left, top = (size - width) // 2, (size - height) // 2
        return TF.pad(image, [left, top, size - width - left, size - height - top], fill=self.fill)


def classifier_transform(training=False, image_size=224, augmentation="basic",
                         mean=(.485, .456, .406), std=(.229, .224, .225), interpolation="bilinear"):
    interpolation_mode = getattr(transforms.InterpolationMode, interpolation.upper(), None)
    if interpolation_mode is None:
        raise ValueError(f"Unknown interpolation mode: {interpolation}")
    ops = [PadToSquare(0), transforms.Resize((image_size, image_size), interpolation=interpolation_mode)]
    if training:
        if augmentation == "autoaugment":
            ops += [transforms.RandomHorizontalFlip(), transforms.AutoAugment(transforms.AutoAugmentPolicy.IMAGENET)]
        elif augmentation == "basic":
            ops += [transforms.RandomHorizontalFlip(), transforms.RandomRotation(10),
                    transforms.ColorJitter(brightness=.15, contrast=.15, saturation=.10)]
        elif augmentation != "none": raise ValueError(f"Unknown augmentation policy: {augmentation}")
    ops += [transforms.ToTensor(), transforms.Normalize(mean, std)]
    return transforms.Compose(ops)


def checkpoint_preprocessing(metadata):
    """Return preprocessing metadata, with defaults for legacy checkpoints."""
    return {"image_size": int(metadata.get("image_size", 224)),
            "mean": tuple(metadata.get("normalization_mean", (.485, .456, .406))),
            "std": tuple(metadata.get("normalization_std", (.229, .224, .225))),
            "interpolation": metadata.get("interpolation", "bilinear")}


def checkpoint_classifier_transform(metadata):
    config = checkpoint_preprocessing(metadata)
    return classifier_transform(False, config["image_size"], "none", config["mean"], config["std"],
                                config["interpolation"])


def load_rgb_standardized(path):
    with Image.open(path) as image:
        return ImageOps.exif_transpose(image).convert("RGB")


def yolo_polygon_mask(label_path, shape):
    height, width = shape[:2]; mask = np.zeros((height, width), np.uint8)
    for line in Path(label_path).read_text(encoding="utf-8").splitlines():
        values = line.split()
        if len(values) < 7 or (len(values) - 1) % 2: continue
        points = np.asarray(values[1:], np.float32).reshape(-1, 2)
        points *= np.asarray([width, height]); cv2.fillPoly(mask, [np.rint(points).astype(np.int32)], 1)
    return mask


def heal_mask(mask, ratio=.01, maximum=31):
    size = max(3, min(maximum, int(min(mask.shape) * ratio))); size += 1 - size % 2
    kernel = np.ones((size, size), np.uint8)
    return cv2.dilate(cv2.morphologyEx((mask > 0).astype(np.uint8), cv2.MORPH_CLOSE, kernel), kernel)


@dataclass
class ROI:
    image: np.ndarray
    mask: np.ndarray
    bbox: tuple
    confidence: float | None = None


def crop_from_mask(image, mask, context=1.30, heal=True):
    if mask.shape != image.shape[:2]:
        mask = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    mask = heal_mask(mask) if heal else (mask > 0).astype(np.uint8)
    ys, xs = np.where(mask > 0)
    if not len(xs): raise ValueError("empty mask")
    x1, x2, y1, y2 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
    px, py = int((x2-x1)*(context-1)/2), int((y2-y1)*(context-1)/2)
    x1, x2 = max(0, x1-px), min(image.shape[1], x2+px)
    y1, y2 = max(0, y1-py), min(image.shape[0], y2+py)
    return ROI(image[y1:y2, x1:x2].copy(), mask, (x1, y1, x2, y2))


def predict_roi(model, image, conf=.25, imgsz=640, device="cpu", context=1.30):
    results = model.predict(source=image, conf=conf, imgsz=imgsz, device=device,
                            retina_masks=True, verbose=False)
    
    if not results or results[0].masks is None or results[0].boxes is None or not len(results[0].boxes):
        raise ValueError("no snake instance detected")
    
    result = results[0]; index = int(result.boxes.conf.argmax().item())
    roi = crop_from_mask(image, (result.masks.data[index].cpu().numpy() >= .5).astype(np.uint8), context)
    roi.confidence = float(result.boxes.conf[index].item())
    return roi
