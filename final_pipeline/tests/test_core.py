import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import torch
from torch import nn
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from snake_pipeline.config import SPECIES, VENOM_LOOKUP
from snake_pipeline.explainability import map_cam_to_original, normalize_cam, remove_square_padding
from snake_pipeline.image_ops import PadToSquare, checkpoint_classifier_transform, checkpoint_preprocessing, crop_from_mask
from snake_pipeline.mobilevit import build_mobilevit
from snake_pipeline.models import load_checkpoint
from snake_pipeline.safety import gate


class CoreTests(unittest.TestCase):
    def test_configuration(self): self.assertEqual((len(SPECIES), len(VENOM_LOOKUP)), (8, 8))
    def test_square_padding(self): self.assertEqual(PadToSquare()(Image.new("RGB", (1200, 800))).size, (1200, 1200))
    def test_checkpoint_preprocessing(self):
        metadata = {"image_size": 256, "normalization_mean": [0, 0, 0],
                    "normalization_std": [1, 1, 1], "interpolation": "bicubic"}
        self.assertEqual(checkpoint_preprocessing(metadata)["image_size"], 256)
        tensor = checkpoint_classifier_transform(metadata)(Image.new("RGB", (1200, 800)))
        self.assertEqual(tuple(tensor.shape), (3, 256, 256))
    def test_legacy_checkpoint_preprocessing(self):
        self.assertEqual(checkpoint_preprocessing({})["image_size"], 224)
    def test_mobilevit_dual_arcface_checkpoint_round_trip(self):
        class DummyBackbone(nn.Module):
            num_features = 4
            def __init__(self):
                super().__init__(); self.projection = nn.Linear(3, 4)
            def forward(self, tensor):
                return self.projection(tensor.mean((2, 3)))
        fake_timm = SimpleNamespace(create_model=lambda *args, **kwargs: DummyBackbone())
        with patch("snake_pipeline.mobilevit._timm", return_value=fake_timm):
            model = build_mobilevit("mobilevit_xs.cvnets_in1k", len(SPECIES), False,
                                    head_type="arcface", dual_head=True)
            checkpoint = {"model_family": "timm_mobilevit", "timm_model": "mobilevit_xs.cvnets_in1k",
                          "architecture": "mobilevit_xs.cvnets_in1k", "class_names": SPECIES,
                          "head_type": "arcface", "dual_head": True, "model_state": model.state_dict(),
                          "image_size": 256, "normalization_mean": [0, 0, 0],
                          "normalization_std": [1, 1, 1], "interpolation": "bicubic"}
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "model.pt"; torch.save(checkpoint, path)
                loaded, _ = load_checkpoint(path, torch.device("cpu"))
                species, venom = loaded(torch.randn(2, 3, 16, 16))
            self.assertEqual(tuple(species.shape), (2, len(SPECIES)))
            self.assertEqual(tuple(venom.shape), (2, 2))
    def test_crop(self):
        image=np.zeros((100,200,3),np.uint8); mask=np.zeros((100,200),np.uint8); mask[20:80,50:150]=1
        self.assertGreater(crop_from_mask(image,mask).image.size, 0)
    def test_contradiction_withholds(self):
        prediction={"detector_confidence":.9,"species_confidence":.9,"species_margin":.8,"agreement":1.,
                    "normalized_entropy":.1,"venom_consistent":False}
        self.assertEqual(gate(prediction)[0], "WITHHOLD")
    def test_gradcam_mapping(self):
        normalized = normalize_cam(torch.tensor([[[1., 2.], [3., 5.]]]))
        self.assertAlmostEqual(float(normalized.min()), 0.)
        self.assertAlmostEqual(float(normalized.max()), 1.)
        native = remove_square_padding(np.ones((16, 16), np.float32), 20, 10)
        self.assertEqual(native.shape, (10, 20))
        original = np.zeros((30, 40, 3), np.uint8)
        full, overlay = map_cam_to_original(original, native, (5, 5, 25, 15))
        self.assertEqual(full.shape, (30, 40))
        self.assertEqual(overlay.shape, original.shape)


if __name__ == "__main__": unittest.main()
