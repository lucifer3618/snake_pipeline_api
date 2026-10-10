# End-to-end detector cascade + cross-fold dual-head classifier ensemble inference.
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
import cv2
import torch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
os.environ.setdefault("YOLO_CONFIG_DIR", tempfile.gettempdir())
from ultralytics import YOLO
from snake_pipeline.ensemble import FoldEnsemble
from snake_pipeline.image_ops import predict_roi
from snake_pipeline.safety import gate
from PIL import Image


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--image",required=True, help= "Path to input image")
    parser.add_argument("--detector",required=True, help="Path to YOLOv11 primary detector checkpoint")
    parser.add_argument("--secondary_detector",required=False, help="Path to YOLOv11 secondary detector checkpoint")
    parser.add_argument("--conf",type=float,default=0.25, help="Confidence threshold for primary detector")
    parser.add_argument("--retry_conf",type=float,default=0.25, help="Confidence threshold for retry detector")
    parser.add_argument("--retry_imgsz",type=int,default=640, help="Image size for retry detector; must match training size")
    parser.add_argument("--classifiers",nargs="+",required=True, help="Paths to cross-fold dual-head classifier checkpoints")
    parser.add_argument("--thresholds",required=True, help="Path to thresholds file")
    parser.add_argument("--device",default="cuda:0", help="Device to run inference on; use 'cpu' for CPU-only inference")
    parser.add_argument("--imgsz",type=int,default=640, help="Image size for primery YOLOv11 detector; must match training size")
    args=parser.parse_args()

    device_name=args.device if not args.device.startswith("cuda") or torch.cuda.is_available() else "cpu";
    device=torch.device(device_name)

    thresholds=json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
    image=cv2.imread(args.image)

    primary_detector=YOLO(args.detector)
    secondary_detector=YOLO(args.secondary_detector) if args.secondary_detector else None

    if image is None:
        raise SystemExit(f"Cannot read {args.image}")
    
    try: 
        # Defined ROI detection attempts across models
        attempts = [
            (
                "primary",
                primary_detector,
                args.conf,
                args.imgsz,
            ),
            (
                "primary_retry",
                primary_detector,
                args.retry_conf,
                args.retry_imgsz,
            ),
            (
                "secondary_retry",
                secondary_detector,
                args.retry_conf,
                args.retry_imgsz,
            ),
        ]

        roi = None
        detector_stage = None
        detector_errors = []

        # Goes over each attempt and try predicting the ROI.
        for stage, detector, conf, imgsz in attempts:
            try:
                result = predict_roi(
                    image=image,
                    detector=detector,
                    conf=conf,
                    imgsz=imgsz,
                    device=device
                )
                if result is not None:
                    roi = result
                    detector_stage = stage
                    break
                else:
                    detector_errors.append(f"{stage}: No ROI detected")
            except Exception as error:
                detector_errors.append(f"{stage}: {error}")
        if roi is None:
            print(json.dumps({"decision":"WITHHOLD","reasons":detector_errors or ["no snake instance detected"]},indent=2))
            return
    except Exception as error:
        print(json.dumps({"decision":"WITHHOLD","reasons":[str(error)]},indent=2))
        return
    
    ensemble=FoldEnsemble(args.classifiers,device)
    tensor=ensemble.transform(Image.fromarray(roi.image[:,:,::-1])).unsqueeze(0).to(device)

    result=ensemble.predict(tensor)
    result["detector_confidence"]=roi.confidence
    result["detector_stage"]=detector_stage

    decision,reasons=gate(result, thresholds)

    result.update({"decision":decision, "reasons":reasons, "detector_stage":detector_stage, "bbox":roi.bbox})

    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
