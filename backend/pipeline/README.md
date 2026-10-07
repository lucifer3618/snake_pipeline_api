# Bundled inference pipeline

This directory contains everything the API needs from the trained final pipeline:

- `src/snake_pipeline/` — inference, model construction, transforms, ROI extraction, ensemble, and safety-gate code.
- `config/species.yaml` — ordered species and venom labels used by the checkpoints.
- `models/detectors/` — selected primary `seg_model_s_2` and fallback `seg_model_n_3` instance-segmentation checkpoints.
- `models/classifiers/` — the five selected MobileViT ArcFace+Focal fold checkpoints.

The API adds `pipeline/src` to Python's import path during model loading. No file from the repository-level `final_pipeline` directory is accessed at runtime.

`config/gate_thresholds.json` is optional. When it is absent, the bundled `snake_pipeline.safety.DEFAULT_THRESHOLDS` values are used.
