import math
import torch
import torch.nn.functional as F
from .config import SPECIES, VENOM_LOOKUP
from .image_ops import checkpoint_classifier_transform, checkpoint_preprocessing
from .models import load_checkpoint


class FoldEnsemble:
    def __init__(self, checkpoints, device):
        self.device = device; self.models = []; self.metadata = []
        for path in checkpoints:
            model, metadata = load_checkpoint(path, device)
            if metadata["class_names"] != SPECIES or not model.dual_head:
                raise ValueError(f"{path} is not a compatible dual-head checkpoint")
            self.models.append(model); self.metadata.append(metadata)
        if not self.models: raise ValueError("No ensemble checkpoints supplied")
        reference = self.metadata[0]
        signature = (reference.get("model_family", "torchvision"), reference.get("timm_model", reference["architecture"]),
                     reference.get("head_type", "linear"), reference.get("loss", "ce"))
        folds = [metadata.get("fold") for metadata in self.metadata]
        if len(set(folds)) != len(folds):
            raise ValueError(f"Duplicate ensemble fold checkpoints: {folds}")
        for path, metadata in zip(checkpoints[1:], self.metadata[1:]):
            candidate = (metadata.get("model_family", "torchvision"), metadata.get("timm_model", metadata["architecture"]),
                         metadata.get("head_type", "linear"), metadata.get("loss", "ce"))
            if candidate != signature:
                raise ValueError(f"Checkpoint model/loss mismatch: {path}")
        preprocessing = checkpoint_preprocessing(self.metadata[0])
        for path, metadata in zip(checkpoints[1:], self.metadata[1:]):
            if checkpoint_preprocessing(metadata) != preprocessing:
                raise ValueError(f"Checkpoint preprocessing mismatch: {path}")
        self.preprocessing = preprocessing
        self.transform = checkpoint_classifier_transform(self.metadata[0])

    @torch.no_grad()
    def predict(self, tensor):
        species_members, venom_members = [], []
        for model in self.models:
            species, venom = model(tensor); species_members.append(F.softmax(species, 1)); venom_members.append(F.softmax(venom, 1))
        species_probs = torch.stack(species_members).mean(0)[0]; venom_probs = torch.stack(venom_members).mean(0)[0]
        predicted = int(species_probs.argmax()); venom = int(venom_probs.argmax()); member_votes = [int(p[0].argmax()) for p in species_members]
        top2 = species_probs.topk(2); entropy = float(-(species_probs * torch.log(species_probs.clamp_min(1e-9))).sum() / math.log(len(SPECIES)))
        return {"predicted_index": predicted, "predicted_species": SPECIES[predicted],
                "species_confidence": float(top2.values[0]), "species_margin": float(top2.values[0]-top2.values[1]),
                "normalized_entropy": entropy, "agreement": member_votes.count(predicted)/len(member_votes),
                "member_votes": member_votes, "predicted_venom": venom, "venom_confidence": float(venom_probs[venom]),
                "expected_venom": VENOM_LOOKUP[predicted], "venom_consistent": venom == VENOM_LOOKUP[predicted]}
