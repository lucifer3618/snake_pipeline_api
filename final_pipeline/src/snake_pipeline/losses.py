import math
import torch
import torch.nn.functional as F
from torch import nn


class ArcMarginProduct(nn.Module):
    """ArcFace cosine classifier; applies the angular margin only when labels are supplied."""
    def __init__(self, features, classes, scale=64.0, margin=0.5):
        super().__init__(); self.scale, self.margin = scale, margin
        self.weight = nn.Parameter(torch.empty(classes, features)); nn.init.xavier_uniform_(self.weight)
        self.cos_m, self.sin_m = math.cos(margin), math.sin(margin)
        self.threshold, self.mm = math.cos(math.pi-margin), math.sin(math.pi-margin)*margin

    def forward(self, features, labels=None):
        cosine = F.linear(F.normalize(features), F.normalize(self.weight)).clamp(-1+1e-7, 1-1e-7)
        if labels is None: return cosine * self.scale
        sine = torch.sqrt((1.0-cosine.square()).clamp_min(1e-7)); phi = cosine*self.cos_m-sine*self.sin_m
        phi = torch.where(cosine > self.threshold, phi, cosine-self.mm)
        one_hot = F.one_hot(labels, num_classes=cosine.shape[1]).to(cosine.dtype)
        return (one_hot*phi + (1-one_hot)*cosine) * self.scale


class FocalLoss(nn.Module):
    def __init__(self, gamma=2.0, alpha=None):
        super().__init__(); self.gamma, self.alpha = gamma, alpha
    def forward(self, logits, targets):
        log_probs=F.log_softmax(logits,dim=1); probs=log_probs.exp(); indices=targets.unsqueeze(1)
        log_pt=log_probs.gather(1,indices).squeeze(1); pt=probs.gather(1,indices).squeeze(1)
        loss=-(1-pt).pow(self.gamma)*log_pt
        if self.alpha is not None: loss=loss*self.alpha.to(logits.device)[targets]
        return loss.mean()
