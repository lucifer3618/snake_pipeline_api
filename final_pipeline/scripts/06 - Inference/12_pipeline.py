"""End-to-end single detector + cross-fold dual-head classifier ensemble inference."""
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
    parser.add_argument("--detector",required=True, help="Path to YOLOv8 detector checkpoint")
    parser.add_argument("--classifiers",nargs="+",required=True, help="Paths to cross-fold dual-head classifier checkpoints")
    parser.add_argument("--thresholds",required=True, help="Path to thresholds file")
    parser.add_argument("--device",default="cuda:0", help="Device to run inference on; use 'cpu' for CPU-only inference")
    parser.add_argument("--imgsz",type=int,default=640, help="Image size for YOLOv8 detector; must match training size")
    args=parser.parse_args()

    device_name=args.device if not args.device.startswith("cuda") or torch.cuda.is_available() else "cpu";
    device=torch.device(device_name)

    thresholds=json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
    image=cv2.imread(args.image)

    if image is None:
        raise SystemExit(f"Cannot read {args.image}")
    try: 
        roi=predict_roi(YOLO(args.detector), image, thresholds["detector_confidence"], args.imgsz,device_name)
    except Exception as error:
        print(json.dumps({"decision":"WITHHOLD","reasons":[str(error)]},indent=2))
        return
    
    ensemble=FoldEnsemble(args.classifiers,device)
    tensor=ensemble.transform(Image.fromarray(roi.image[:,:,::-1])).unsqueeze(0).to(device)

    result=ensemble.predict(tensor)
    result["detector_confidence"]=roi.confidence

    decision,reasons=gate(result, thresholds)

    result.update({"decision":decision, "reasons":reasons, "bbox":roi.bbox})

    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
