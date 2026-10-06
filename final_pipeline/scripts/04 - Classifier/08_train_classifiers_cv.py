"""Train all requested classifier architectures across all prepared folds."""
import argparse
import csv
import json
import random
import sys
from copy import deepcopy
from pathlib import Path
import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from tqdm import tqdm
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from snake_pipeline.config import SPECIES, VENOM_LOOKUP
from snake_pipeline.data import loaders
from snake_pipeline.models import ARCHITECTURES, build_model
from snake_pipeline.losses import FocalLoss


def seed_all(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)


def mix_batch(images, labels, method, alpha, probability):
    if method == "none" or random.random() >= probability or len(images) < 2: return images, labels, labels, 1.0
    chosen = random.choice(["mixup", "cutmix"]) if method == "random" else method
    permutation = torch.randperm(len(images), device=images.device); labels_b = labels[permutation]
    lam = float(np.random.beta(alpha, alpha))
    if chosen == "mixup": return lam*images + (1-lam)*images[permutation], labels, labels_b, lam
    _, _, height, width = images.shape; ratio = np.sqrt(1-lam); cut_w, cut_h = int(width*ratio), int(height*ratio)
    center_x, center_y = random.randrange(width), random.randrange(height)
    x1, x2 = max(0,center_x-cut_w//2), min(width,center_x+cut_w//2)
    y1, y2 = max(0,center_y-cut_h//2), min(height,center_y+cut_h//2)
    mixed=images.clone(); mixed[:,:,y1:y2,x1:x2]=images[permutation,:,y1:y2,x1:x2]
    lam=1-((x2-x1)*(y2-y1)/(width*height)); return mixed, labels, labels_b, lam


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval(); truth, predicted = [], []
    for images, labels in loader:
        output = model(images.to(device)); logits = output[0] if isinstance(output, tuple) else output
        truth.extend(labels.tolist()); predicted.extend(logits.argmax(1).cpu().tolist())
    metrics = {"accuracy": accuracy_score(truth, predicted),
            "macro_precision": precision_score(truth, predicted, average="macro", zero_division=0),
            "macro_recall": recall_score(truth, predicted, average="macro", zero_division=0),
            "macro_f1": f1_score(truth, predicted, average="macro", zero_division=0)}
    return metrics, truth, predicted


def train_one(architecture, fold, args, device):
    seed_all(args.seed + fold); fold_dir = Path(args.data_root) / f"fold_{fold}"
    data_loaders, datasets = loaders(fold_dir, args.batch, args.workers, args.image_size, args.image_augmentation)
    head_type = "arcface" if args.loss.startswith("arcface") else "linear"
    model = build_model(architecture, len(SPECIES), args.pretrained, args.dropout, head_type,
                        args.arc_scale, args.arc_margin, args.dual_head).to(device)
    experiment = f"{architecture}__{'dual__' if model.dual_head else ''}{args.loss}"
    output = Path(args.output) / experiment / f"fold_{fold}"
    output.mkdir(parents=True, exist_ok=True)
    if (output / "best.pt").exists() and not args.overwrite:
        raise SystemExit(f"Completed checkpoint already exists: {output / 'best.pt'}; choose a new output or pass --overwrite")
    run_config = {**vars(args), "architecture": architecture, "fold": fold,
                  "experiment": experiment, "device": str(device), "torch_version": torch.__version__}
    (output / "run_config.json").write_text(json.dumps(run_config, indent=2), encoding="utf-8")
    writer = None
    if args.tracker == "tensorboard":
        try:
            from torch.utils.tensorboard import SummaryWriter
        except ImportError as error:
            raise SystemExit("TensorBoard is not installed; run: pip install tensorboard") from error
        writer = SummaryWriter(log_dir=str(output / "tensorboard"))
    if args.freeze_backbone_epochs:
        if not args.pretrained:
            raise SystemExit("--freeze-backbone-epochs requires --pretrained")
        for parameter in model.features[0].parameters(): parameter.requires_grad = False
    species_loss = nn.CrossEntropyLoss(label_smoothing=args.label_smoothing)
    lookup = torch.tensor(VENOM_LOOKUP, device=device)
    targets = torch.tensor(datasets["train"].targets); venom_targets = torch.tensor(VENOM_LOOKUP)[targets]
    species_counts = torch.bincount(targets, minlength=len(SPECIES)).float()
    if args.focal_alpha == "balanced":
        focal_alpha = species_counts.sum() / (len(SPECIES) * species_counts.clamp_min(1)); focal_alpha /= focal_alpha.mean()
    else:
        focal_alpha = torch.full((len(SPECIES),), float(args.focal_alpha))
    focal_loss = FocalLoss(args.focal_gamma, focal_alpha)
    counts = torch.bincount(venom_targets, minlength=2).float(); venom_loss = nn.CrossEntropyLoss(weight=(counts.sum()/(2*counts)).to(device))
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = (CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=args.min_lr)
                 if args.scheduler == "cosine" else None)
    scaler = torch.amp.GradScaler("cuda", enabled=args.amp and device.type == "cuda")
    best, best_state, bad, history = -1., None, 0, []
    for epoch in range(args.epochs):
        if epoch == args.freeze_backbone_epochs and args.freeze_backbone_epochs:
            for parameter in model.features[0].parameters(): parameter.requires_grad = True
        model.train(); total_loss = 0.
        for images, labels in tqdm(data_loaders["train"], leave=False, desc=f"{architecture} f{fold} e{epoch+1}"):
            images, labels = images.to(device), labels.to(device); images, labels_a, labels_b, lam = mix_batch(
                images, labels, args.batch_augmentation, args.mix_alpha, args.mix_probability)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast(device_type=device.type, enabled=scaler.is_enabled()):
                features=model.extract_features(images)
                logits_a=model.classify_features(features, labels_a if head_type == "arcface" else None)
                logits_b=model.classify_features(features, labels_b if head_type == "arcface" else None)
                objective=lambda logits,target: species_loss(logits,target) + (args.focal_weight*focal_loss(logits,target) if args.loss.endswith("focal") else 0)
                loss=lam*objective(logits_a,labels_a)+(1-lam)*objective(logits_b,labels_b)
                if model.dual_head:
                    venom_logits=model.venom_head(features)
                    loss += args.venom_weight*(lam*venom_loss(venom_logits,lookup[labels_a])+(1-lam)*venom_loss(venom_logits,lookup[labels_b]))
            scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update(); total_loss += loss.item() * len(labels)
        metrics, _, _ = evaluate(model, data_loaders["validation"], device)
        current_lr = optimizer.param_groups[0]["lr"]
        epoch_row = {"epoch": epoch + 1, "train_loss": total_loss/len(datasets["train"]),
                     "learning_rate": current_lr,
                     "backbone_frozen": epoch < args.freeze_backbone_epochs, **metrics}
        history.append(epoch_row)
        with (output / "training_history.csv").open("w", newline="", encoding="utf-8") as handle:
            history_writer = csv.DictWriter(handle, fieldnames=history[0])
            history_writer.writeheader(); history_writer.writerows(history)
        if writer is not None:
            writer.add_scalar("loss/train", epoch_row["train_loss"], epoch + 1)
            writer.add_scalar("metrics/validation_macro_f1", metrics["macro_f1"], epoch + 1)
            writer.add_scalar("metrics/validation_accuracy", metrics["accuracy"], epoch + 1)
            writer.add_scalar("metrics/validation_macro_precision", metrics["macro_precision"], epoch + 1)
            writer.add_scalar("metrics/validation_macro_recall", metrics["macro_recall"], epoch + 1)
            writer.add_scalar("optimization/learning_rate", current_lr, epoch + 1)
            writer.flush()
        print(f"{architecture} fold={fold} epoch={epoch+1} loss={total_loss/len(datasets['train']):.4f} macro_f1={metrics['macro_f1']:.4f} lr={current_lr:.3e}")
        if metrics["macro_f1"] > best:
            best, best_state, bad = metrics["macro_f1"], deepcopy(model.state_dict()), 0
        else:
            bad += 1
        if scheduler is not None: scheduler.step()
        if bad >= args.patience: break
    if writer is not None: writer.close()
    checkpoint = {"architecture": architecture, "class_names": SPECIES, "venom_lookup": VENOM_LOOKUP,
                  "dropout": args.dropout, "fold": fold, "loss": args.loss, "head_type": head_type,
                  "dual_head": model.dual_head,
                  "arc_scale": args.arc_scale, "arc_margin": args.arc_margin,
                  "image_augmentation": args.image_augmentation, "batch_augmentation": args.batch_augmentation,
                  "scheduler": args.scheduler, "learning_rate": args.lr, "minimum_learning_rate": args.min_lr,
                  "freeze_backbone_epochs": args.freeze_backbone_epochs,
                  "best_macro_f1": best, "model_state": best_state}
    torch.save(checkpoint, output / "best.pt"); model.load_state_dict(best_state)
    metrics, truth, predicted = evaluate(model, data_loaders["validation"], device)
    metrics.update({"experiment": experiment, "architecture": architecture, "loss": args.loss, "fold": fold,
                    "parameters": sum(parameter.numel() for parameter in model.parameters())})
    (output / "validation_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    with (output / "validation_predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["true_index", "predicted_index"]); writer.writeheader()
        writer.writerows({"true_index": true, "predicted_index": pred} for true, pred in zip(truth, predicted))
    return metrics


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--data-root", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--architectures", nargs="+", choices=ARCHITECTURES, default=list(ARCHITECTURES))
    parser.add_argument("--folds", nargs="+", type=int, default=[0,1,2,3,4]); parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch", type=int, default=32); parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--image-size", type=int, default=224); parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--scheduler", choices=["cosine", "none"], default="cosine")
    parser.add_argument("--min-lr", type=float, default=1e-6)
    parser.add_argument("--weight-decay", type=float, default=1e-4); parser.add_argument("--dropout", type=float, default=.2)
    parser.add_argument("--label-smoothing", type=float, default=0.0); parser.add_argument("--venom-weight", type=float, default=.25)
    parser.add_argument("--loss", choices=["ce", "ce_focal", "arcface", "arcface_focal"], default="ce")
    parser.add_argument("--focal-gamma", type=float, default=2.0); parser.add_argument("--focal-alpha", default="balanced")
    parser.add_argument("--focal-weight", type=float, default=1.0)
    parser.add_argument("--arc-scale", type=float, default=64.0); parser.add_argument("--arc-margin", type=float, default=.5)
    parser.add_argument("--image-augmentation", choices=["none","basic","autoaugment"], default="basic")
    parser.add_argument("--batch-augmentation", choices=["none","mixup","cutmix","random"], default="none")
    parser.add_argument("--mix-alpha", type=float, default=.2); parser.add_argument("--mix-probability", type=float, default=.25)
    parser.add_argument("--patience", type=int, default=5); parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--freeze-backbone-epochs", type=int, default=2)
    parser.add_argument("--tracker", choices=["tensorboard", "none"], default="tensorboard")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--dual-head", action="store_true", help="Add the venomous/non-venomous auxiliary head")
    parser.add_argument("--pretrained", action="store_true"); parser.add_argument("--amp", action="store_true"); args = parser.parse_args()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu"); results = []
    for architecture in args.architectures:
        for fold in args.folds: results.append(train_one(architecture, fold, args, device))
    path = Path(args.output) / "cv_training_summary.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0]); writer.writeheader(); writer.writerows(results)


if __name__ == "__main__": main()
