import torch
from torch import nn
from torchvision.models import (EfficientNet_B0_Weights, MobileNet_V2_Weights,
                                efficientnet_b0, mobilenet_v2)
from .attention import CBAM, SEBlock
from .losses import ArcMarginProduct

ARCHITECTURES = ("mobilenet_v2", "mobilenet_v2_se", "mobilenet_v2_cbam", "efficientnet_b0", "efficientnet_b0_dual")


class Classifier(nn.Module):
    def __init__(self, architecture, classes, pretrained=True, dropout=.2, head_type="linear", arc_scale=64., arc_margin=.5,
                 dual_head=None, attention_reduction=16, cbam_kernel=7):
        super().__init__(); self.architecture = architecture
        self.dual_head = architecture.endswith("_dual") if dual_head is None else dual_head
        backbone_name = architecture.removesuffix("_dual")
        if backbone_name.startswith("mobilenet"):
            base = mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V1 if pretrained else None); width = 1280
            attention = (SEBlock(width, attention_reduction) if backbone_name.endswith("_se")
                         else CBAM(width, attention_reduction, cbam_kernel) if backbone_name.endswith("_cbam")
                         else nn.Identity())
        else:
            base = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1 if pretrained else None); width = 1280; attention = nn.Identity()
        self.features = nn.Sequential(base.features, attention)
        self.pool = nn.AdaptiveAvgPool2d(1); self.dropout = nn.Dropout(dropout)
        self.head_type = head_type
        self.species_head = (ArcMarginProduct(width, classes, arc_scale, arc_margin)
                             if head_type == "arcface" else nn.Linear(width, classes))
        self.venom_head = nn.Linear(width, 2) if self.dual_head else None

    def extract_features(self, x): return self.dropout(torch.flatten(self.pool(self.features(x)), 1))
    def classify_features(self, features, labels=None):
        return self.species_head(features, labels) if self.head_type == "arcface" else self.species_head(features)
    def forward(self, x, labels=None):
        features = self.extract_features(x); species = self.classify_features(features, labels)
        return (species, self.venom_head(features)) if self.dual_head else species


def build_model(architecture, classes, pretrained=True, dropout=.2, head_type="linear", arc_scale=64., arc_margin=.5,
                dual_head=None, attention_reduction=16, cbam_kernel=7):
    if architecture not in ARCHITECTURES: raise ValueError(f"Unknown architecture {architecture}")
    return Classifier(architecture, classes, pretrained, dropout, head_type, arc_scale, arc_margin, dual_head,
                      attention_reduction, cbam_kernel)


def load_checkpoint(path, device):
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    if checkpoint.get("model_family") == "timm_mobilevit":
        from .mobilevit import build_mobilevit
        model = build_mobilevit(checkpoint.get("timm_model", checkpoint["architecture"]),
                                len(checkpoint["class_names"]), False, checkpoint.get("dropout", .2),
                                checkpoint.get("head_type", "linear"), checkpoint.get("arc_scale", 64.),
                                checkpoint.get("arc_margin", .5), checkpoint.get("dual_head", False))
    else:
        model = build_model(checkpoint["architecture"], len(checkpoint["class_names"]), False, checkpoint.get("dropout", .2),
                            checkpoint.get("head_type", "linear"), checkpoint.get("arc_scale", 64.), checkpoint.get("arc_margin", .5),
                            checkpoint.get("dual_head"), checkpoint.get("attention_reduction", 16), checkpoint.get("cbam_kernel", 7))
    model.load_state_dict(checkpoint["model_state"], strict=True)
    return model.to(device).eval(), checkpoint
