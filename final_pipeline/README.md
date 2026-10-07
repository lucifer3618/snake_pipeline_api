# 06 - Final Pipeline

This directory is the clean, standalone implementation. Sections 01–05 remain unchanged as the chronological experiments and gradual improvements used to motivate the final design.

## Final research design

```text
original images
  -> non-destructive rename
  -> EXIF/RGB/format standardization (no resize, no black bars)
  -> original-resolution instance-segmentation annotation
  -> grouped train_pool / calibration / test split
  -> 5 folds inside train_pool
  -> compare YOLO segmentation sizes
  -> native-resolution ROI extraction
  -> compare five classifier architectures with identical folds
  -> cross-fold dual-head MobileViT-XS ensemble with ArcFace + Focal loss
  -> calibrated safety gate
  -> one untouched test evaluation
```

The primary controlled comparison is standardized `whole` images versus detector-extracted `predicted_roi` images using matched source images and identical fold assignments.

## Why ROI images are not permanently resized

`07b_build_fixed_detector_dataset.py` saves native-resolution ROI crops. Both training and inference then use the exact same classifier transform:

1. pad the shorter dimension to a square with black pixels;
2. resize the square to the network input size;
3. apply ImageNet normalization.

This preserves the original aspect ratio, avoids irreversible preprocessing, and prevents `CenterCrop` or `RandomResizedCrop` from cutting away the snake. Training-only augmentation happens after square padding. CLAHE is excluded from the main experiment; add it only as a separately reported ablation.

## Environment

```powershell
cd "06 - Final Pipeline"
conda env create -f environment.yml
conda activate snake_final_pipeline
pip install -e .
```

Commands below assume the current directory is `06 - Final Pipeline`.

### Linux GPU / Proxmox LXC setup

Do not copy a Windows Conda environment. After transferring this complete
directory, recreate it inside the LXC:

```bash
nvidia-smi
conda env create -f environment.yml
conda activate snake_final_pipeline
pip install -e .
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No CUDA GPU')"
python -m pytest tests -q
```

The environment installs PyTorch and Torchvision through Conda with CUDA 12.1;
the pip requirements deliberately do not reinstall them. Start long training
commands inside `tmux` so they survive a disconnected VS Code/SSH session.

## Script stages

```text
scripts/
|-- 01 - Data Preparation
|-- 02 - Detector
|-- 03 - ROI Extraction
|-- 04 - Classifier
|-- 05 - Ensemble and Safety
`-- 06 - Inference
```

Keep running commands from the project root. Because stage directory names
contain spaces, the script path must remain inside quotes in PowerShell.

## 1. Rename and standardize

Both operations write to new roots and never alter the originals.

```powershell
python "scripts/01 - Data Preparation/01_rename_images.py" --input data/raw --output data/01_renamed
python "scripts/01 - Data Preparation/02_standardize_images.py" --input data/01_renamed --output data/02_standardized
```

Always choose a new, empty output folder. The renamer deliberately stops if the
destination already contains files.

If original filenames contain a real snake/video/source identifier, preserve it during renaming:

```powershell
python "scripts/01 - Data Preparation/01_rename_images.py" --input "PATH_TO_CLASS_FOLDERS" --output data/01_renamed --group-regex "YOUR_SOURCE_REGEX"
```

Do not use the species name as the group. If source identity was already lost, state this as a limitation rather than inventing groups.

## 2. Annotate and audit

Annotate `data/02_standardized` at original resolution using YOLO instance-segmentation polygons. Export labels into a label root with either matching class subfolders or a flat layout.

```powershell
python "scripts/01 - Data Preparation/03b_validate_annotations.py" --images data/02_standardized --labels "PATH_TO_LABELS" --output outputs/data_audit
```

Resolve missing labels, corrupt images, invalid polygons and duplicates before splitting.

## 3. Create leakage-controlled splits

```powershell
python "scripts/01 - Data Preparation/03_create_manifest.py" --images data/02_standardized --output data/manifest.csv --rename-manifest data/01_renamed/rename_manifest.csv
```

Default allocation is 80% `train_pool`, 10% `calibration`, and 10% untouched `test`; five folds are created only inside `train_pool` for classifier cross-validation. All images sharing a group stay together. Detector cross-validation is not used.

## 4. Compare detector architectures

Six YOLO11 instance-segmentation configurations were compared by varying model capacity, input resolution and maximum training epochs. The original checkpoints, `args.yaml`, `results.csv` and plots are retained under `runs/segment/experiments/training_detection/`. The following command shows the configuration of the selected primary detector:

```powershell
python "scripts/02 - Detector/04_train_detector.py" --data-yaml "PATH_TO_DETECTOR_DATA.YAML" --model-type yolo11s-seg.pt --epochs 150 --imgsz 512 --batch 8 --project runs/segment/experiments/training_detection --name seg_model_s_2 --device 0
python "scripts/02 - Detector/05_evaluate_detector.py" --data-yaml "PATH_TO_DETECTOR_DATA.YAML" --weights "runs/segment/experiments/training_detection/seg_model_s_2/weights/best.pt" --split val --imgsz 512 --experiment seg_model_s_2 --output outputs/detector_selection.csv --device 0
```

Selection prioritized mask mAP50-95, mask mAP50 and mask recall. `seg_model_s_2` was selected as the primary detector and `seg_model_n_3` as the secondary fallback. Retraining is not required for the final demonstration.

## 5. Generate classifier inputs

Use the frozen `seg_model_s_2` checkpoint for the primary pass and higher-resolution retry, followed by `seg_model_n_3` when both primary attempts fail. The script reads the existing split and fold assignments from the manifest; it does not create new random splits.

```powershell
python "scripts/03 - ROI Extraction/07b_build_fixed_detector_dataset.py" --manifest data/manifest.csv --images data/02_standardized --detector "runs/segment/experiments/training_detection/seg_model_s_2/weights/best.pt" --secondary-detector "runs/segment/experiments/training_detection/seg_model_n_3/weights/best.pt" --output data/04_classifier_inputs --conf 0.25 --imgsz 512 --retry-conf 0.10 --retry-imgsz 768 --context 1.30 --device 0
```

The script saves native-resolution crops, uses hard links where supported to avoid duplicating image data across folds, and records detection stage, confidence and failures in `data/04_classifier_inputs/generation_audit.csv`. Never silently remove detector failures from the final end-to-end denominator.

## 6. Compare classifiers with five-fold CV

Train all requested architectures on the deployable predicted ROIs:

```powershell
python "scripts/04 - Classifier/08_train_classifiers_cv.py" --data-root data/04_classifier_inputs/predicted_roi --output runs/classifiers_predicted_roi --architectures mobilenet_v2 mobilenet_v2_se mobilenet_v2_cbam efficientnet_b0 --loss ce --folds 0 1 2 3 4 --epochs 25 --batch 32 --pretrained --amp
python "scripts/04 - Classifier/09_summarize_classifiers.py" --runs runs/classifiers_predicted_roi --loss ce --require-folds 5 --output outputs/classifier_comparison.csv --selection-output outputs/selected_architecture.json
```

Train MobileViT-XS as an additional CE-only candidate with the same folds and
training loop. Its pretrained checkpoint preprocessing is resolved through
`timm`; square padding and the existing training augmentation remain unchanged:

```bash
python "scripts/04 - Classifier/08c_train_mobilevit_cv.py" \
  --data-root data/04_classifier_inputs/predicted_roi \
  --output runs/classifiers_mobilevit \
  --model mobilevit_xs.cvnets_in1k \
  --preprocessing model \
  --folds 0 1 2 3 4 \
  --epochs 25 \
  --batch 32 \
  --pretrained \
  --amp
```

Use `--preprocessing shared` only for a strict identical-transform ablation; it
uses the existing 224-pixel ImageNet transform. Do not compare a model-preprocess
run and silently describe it as an architecture-only comparison. The MobileViT
script records the resolved size, normalization and interpolation in its run
configuration and checkpoints.

The architecture comparison uses one shared training loop. With `--pretrained`,
the backbone is frozen for the first two epochs while the new head (and any SE or
CBAM module) warms up; the complete network is then unfrozen and fine-tuned.
Change this consistently for every candidate with `--freeze-backbone-epochs`.

Every fold writes:

- `run_config.json` with the complete reproducibility configuration;
- `training_history.csv` with loss, learning rate and validation metrics;
- `tensorboard/` event logs;
- `best.pt`, validation metrics and predictions.

Monitor all architectures and folds locally with:

```powershell
python -m tensorboard.main --logdir runs/classifiers_predicted_roi --port 6006
```

Then open `http://localhost:6006`. Use a new output root for a genuinely new
experiment; completed checkpoints are not overwritten unless `--overwrite` is
explicitly supplied.

### Tune SE and CBAM without changing the baseline trainer

The attention search has a separate entry point. It reuses the baseline
trainer's training and evaluation functions but varies only SE/CBAM-specific
parameters. The complete grid below evaluates SE reduction ratios `4, 8, 16,
32` and the same CBAM ratios with spatial kernels `3, 7`. Across five folds this
is 60 runs:

```bash
python "scripts/04 - Classifier/08b_train_attention_tuning_cv.py" \
  --data-root data/04_classifier_inputs/predicted_roi \
  --output runs/attention_tuning \
  --reductions 4 8 16 32 \
  --cbam-kernels 3 7 \
  --folds 0 1 2 3 4 \
  --epochs 25 \
  --batch 32 \
  --pretrained \
  --amp
```

Completed fold checkpoints are skipped automatically when the command is
restarted. Results are ranked in
`runs/attention_tuning/attention_tuning_summary.csv`. Select the best SE
configuration and best CBAM configuration by mean five-fold macro F1, then
compare both with the original MobileNetV2 and EfficientNet-B0 CE baselines.
Do not use the calibration or test partitions during this search.

Report mean ± standard deviation for accuracy, macro precision, macro recall and macro F1. Select by mean macro F1.

### Advanced augmentation ablation

The defaults use conservative image augmentation and no batch mixing. Evaluate advanced methods as controlled alternatives:

```powershell
python "scripts/04 - Classifier/08_train_classifiers_cv.py" --data-root data/04_classifier_inputs/predicted_roi --output runs/augmentation_auto_mixup --architectures efficientnet_b0 --dual-head --loss ce --image-augmentation autoaugment --batch-augmentation mixup --mix-alpha 0.2 --mix-probability 0.25 --folds 0 1 2 3 4 --pretrained --amp
python "scripts/04 - Classifier/08_train_classifiers_cv.py" --data-root data/04_classifier_inputs/predicted_roi --output runs/augmentation_basic_cutmix --architectures efficientnet_b0 --dual-head --loss ce --image-augmentation basic --batch-augmentation cutmix --mix-alpha 0.2 --mix-probability 0.25 --folds 0 1 2 3 4 --pretrained --amp
```

Mosaic and mild MixUp are configured separately in YOLO training (`--mosaic 0.8 --mixup 0.05 --close-mosaic 10`). Mosaic is never used for ROI classification. Torchvision AutoAugment uses a previously learned ImageNet policy; it does not search for a new optimal policy on this snake dataset. MixUp/CutMix correctly mix both species and venom losses. Compare these runs against the basic baseline before claiming an improvement.

To quantify the ROI contribution, train the selected architecture with identical settings on matched standardized whole images and detector-extracted ROIs, then compare their five-fold results:

When the fixed-detector builder produced only `predicted_roi`, create a matched
whole-image fold view directly from standardized images. This uses the same
manifest assignments and only image IDs successfully cropped by the detector:

```bash
python "scripts/03 - ROI Extraction/07d_build_whole_image_folds.py" \
  --manifest data/manifest.csv \
  --images data/02_standardized \
  --audit data/04_classifier_inputs/generation_audit.csv \
  --population matched \
  --output data/whole_image_folds

python "scripts/04 - Classifier/08d_train_mobilevit_losses_cv.py" \
  --data-root data/whole_image_folds \
  --output runs/mobilevit_whole_arcface_focal \
  --model mobilevit_xs.cvnets_in1k \
  --preprocessing model \
  --losses arcface_focal \
  --folds 0 1 2 3 4 \
  --epochs 25 \
  --batch 32 \
  --workers 2 \
  --pretrained
```

Use `--population all` without `--audit` only for a separately labelled
full-dataset baseline. The matched comparison is the primary controlled ROI
ablation.

```powershell
python "scripts/04 - Classifier/13_compare_experiments.py" --experiment mobilevit_xs.cvnets_in1k__dual__arcface_focal --inputs whole=outputs/whole_summary.csv predicted_roi=outputs/predicted_summary.csv --output outputs/roi_comparison.csv
```

## 7. Loss-function ablation

MobileViT-XS won the CE architecture comparison. Attach the dual venom head and
compare the four promised species-loss configurations on MobileViT-XS only.
The fixed auxiliary venom CE term is identical in all four runs, so the loss
comparison remains controlled. MobileViT training is kept in FP32 because AMP
produced non-finite loss in the architecture experiment:

```bash
python "scripts/04 - Classifier/08d_train_mobilevit_losses_cv.py" \
  --data-root data/04_classifier_inputs/predicted_roi \
  --output runs/mobilevit_loss_ablation \
  --model mobilevit_xs.cvnets_in1k \
  --preprocessing model \
  --losses ce ce_focal arcface arcface_focal \
  --folds 0 1 2 3 4 \
  --epochs 25 \
  --batch 32 \
  --workers 2 \
  --pretrained
```

The runner produces `mobilevit_loss_summary.csv` and
`selected_mobilevit_loss.json`, ranked by mean five-fold macro F1. Its CE run is
retrained with the same dual head used by all other loss configurations.

Defaults are ArcFace `scale=64`, `margin=0.5`, and Focal `gamma=2`. For multiclass imbalance, the default `--focal-alpha balanced` derives one weight per species; a single scalar `0.25` weights every species equally and therefore does not correct multiclass imbalance. Tune any alternatives using fold validation only.

The classifier objective is:

```text
L_classifier = L_species + lambda_focal L_focal + lambda_venom L_venom
```

For ArcFace runs, `L_species` is cross-entropy over angular-margin logits, so ArcFace itself supplies the representation-separation pressure. A separate undefined `L_feat` is not claimed. YOLO box/segmentation/localization losses remain detector-training losses because the detector and classifier are trained sequentially, not end-to-end as one differentiable network.

## 8. Cross-fold MobileViT dual-head safety ensemble

The five checkpoints from the winning MobileViT loss are the five ensemble
members. Every calibration and test image is unseen by every member because
those partitions were excluded before cross-validation.

Use the five checkpoints from the winning loss configuration. The example below assumes ArcFace + Focal won. Generate calibration predictions without applying test-tuned thresholds:

```powershell
python "scripts/05 - Ensemble and Safety/10_evaluate_fold_ensemble.py" --data data/04_classifier_inputs/predicted_roi/fold_0/calibration --checkpoints runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_0/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_1/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_2/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_3/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_4/best.pt --audit data/04_classifier_inputs/generation_audit.csv --split calibration --output outputs/ensemble_calibration
python "scripts/05 - Ensemble and Safety/11_calibrate_gate.py" --predictions outputs/ensemble_calibration/predictions.csv --minimum-coverage 0.50 --output outputs/gate_thresholds.json
```

The gate checks detector confidence, averaged species confidence, top-1/top-2 margin, fold agreement, predictive entropy and species–venom consistency. A contradiction causes withholding; consistency does not prove that the species is correct.

## 9. Final untouched test

Run exactly once after architectures, preprocessing and thresholds are frozen:

```powershell
python "scripts/05 - Ensemble and Safety/10_evaluate_fold_ensemble.py" --data data/04_classifier_inputs/predicted_roi/fold_0/test --checkpoints runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_0/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_1/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_2/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_3/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_4/best.pt --audit data/04_classifier_inputs/generation_audit.csv --split test --thresholds outputs/gate_thresholds.json --output outputs/final_test
```

Report detector mask metrics, classifier CV mean ± SD, ROI ablation, final confusion matrix, end-to-end accuracy, detector coverage, gate coverage, accepted accuracy, contradiction count and latency.

## 10. Deployment-style inference

```powershell
python "scripts/06 - Inference/12_pipeline.py" --image "PATH_TO_IMAGE" --detector "PATH_TO_SELECTED_DETECTOR.PT" --classifiers runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_0/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_1/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_2/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_3/best.pt runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_4/best.pt --thresholds outputs/gate_thresholds.json --device cuda:0
```

The venom grouping in `config/species.yaml` is an operational research label and must be reviewed and cited using qualified Sri Lankan medical/herpetological guidance. The system must be described as decision support, never as a substitute for emergency medical assessment.

## 11. Ensemble Grad-CAM

Generate five fold-specific Grad-CAMs and their normalized ensemble average from
an existing classifier ROI. All members explain the common ensemble top-1 class,
which makes their averaged heatmap interpretable:

```bash
python "scripts/07 - Explainability/14_generate_ensemble_gradcam.py" \
  --roi "PATH_TO_CLASSIFIER_ROI.jpg" \
  --checkpoints \
    runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_0/best.pt \
    runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_1/best.pt \
    runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_2/best.pt \
    runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_3/best.pt \
    runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_4/best.pt \
  --output outputs/gradcam/example \
  --device cuda:0
```

To generate the ROI with the same detector cascade and automatically map the
average CAM back to the original image, use `--image`, `--detector`, and the
optional secondary detector:

```bash
python "scripts/07 - Explainability/14_generate_ensemble_gradcam.py" \
  --image "PATH_TO_ORIGINAL_IMAGE.jpg" \
  --detector "PATH_TO_SEG_MODEL_S_2_BEST.PT" \
  --secondary-detector "PATH_TO_SEG_MODEL_N_3_BEST.PT" \
  --conf 0.25 --imgsz 512 --retry-conf 0.10 --retry-imgsz 768 --context 1.30 \
  --checkpoints \
    runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_0/best.pt \
    runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_1/best.pt \
    runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_2/best.pt \
    runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_3/best.pt \
    runs/mobilevit_loss_ablation/mobilevit_xs.cvnets_in1k__dual__arcface_focal/fold_4/best.pt \
  --thresholds outputs/gate_thresholds.json \
  --output outputs/gradcam/example \
  --device cuda:0
```

The output contains every fold heatmap and overlay, the averaged ensemble map,
the mapped original-image overlay when coordinates are available, the raw
average CAM as NumPy data, and prediction metadata. Grad-CAM is an explanatory
visualization and does not establish causal or biological reasoning.
