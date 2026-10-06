# Detector scripts

These are portable versions of the workflow used for the six YOLO11
instance-segmentation experiments reported in the thesis. Detector
cross-validation was not used; the classifier used five-fold cross-validation.

The original detector runs remain the authoritative evidence under:

```text
01 - Detection_Pipeline/Codes/runs/segment/experiments/training_detection/
```

No detector retraining is required for the final demonstration. The training
script preserves the original Ultralytics `PROJECT/EXPERIMENT_NAME/` layout.

| Experiment | Base checkpoint | Image size | Maximum epochs | Batch |
|---|---|---:|---:|---:|
| `seg_model_n_1` | `yolo11n-seg.pt` | 256 | 100 | 8 |
| `seg_model_n_2` | `yolo11n-seg.pt` | 256 | 200 | 8 |
| `seg_model_n_3` | `yolo11n-seg.pt` | 512 | 100 | 8 |
| `seg_model_s_1` | `yolo11s-seg.pt` | 256 | 150 | 8 |
| `seg_model_s_2` | `yolo11s-seg.pt` | 512 | 150 | 8 |
| `seg_model_m_2` | `yolo11m-seg.pt` | 512 | 150 | 8 |

All other training options use the defaults recorded in each original run's
`args.yaml`.

## Training template

```powershell
python "scripts/02 - Detector/04_train_detector.py" `
  --data-yaml "PATH_TO_DATA.YAML" `
  --model-type "yolo11s-seg.pt" `
  --epochs 150 --batch 8 --imgsz 512 `
  --project "runs/segment/experiments/training_detection" `
  --name "seg_model_s_2" --device 0
```

## Evaluation

```powershell
python "scripts/02 - Detector/05_evaluate_detector.py" `
  --data-yaml "PATH_TO_DATA.YAML" `
  --weights "PATH_TO_SEG_MODEL_S_2/weights/best.pt" `
  --split val --imgsz 512 --experiment "seg_model_s_2" `
  --output "outputs/detector_evaluation.csv" --device 0
```

## Visual verification

```powershell
python "scripts/02 - Detector/06_visualize_detector.py" `
  --source "PATH_TO_IMAGE_OR_DIRECTORY" `
  --weights "PATH_TO_SEG_MODEL_S_2/weights/best.pt" `
  --output-dir "outputs/detector_visualization" --imgsz 512 --device 0
```

`seg_model_s_2` is the primary detector and `seg_model_n_3` is the secondary
fallback. The fallback probe uses only train-pool failures.
