"""Audit standardized images and YOLO segmentation labels before splitting/training."""
import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from snake_pipeline.config import SPECIES


def label_for(root, relative):
    for path in (root / relative.with_suffix(".txt"), root / f"{relative.stem}.txt"):
        if path.exists(): return path
    return None


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--images",required=True); parser.add_argument("--labels",required=True)
    parser.add_argument("--output",required=True); args=parser.parse_args(); images,labels=Path(args.images),Path(args.labels); rows=[]; hashes={}
    for class_dir in sorted(path for path in images.iterdir() if path.is_dir()):
        for path in class_dir.glob("*.jpg"):
            relative=path.relative_to(images); status=[]
            try:
                with Image.open(path) as image: image.verify()
            except Exception as error: status.append(f"invalid_image:{error}")
            label=label_for(labels,relative)
            if label is None: status.append("missing_label")
            else:
                label_lines = [line for line in label.read_text(encoding="utf-8").splitlines() if line.strip()]
                if not label_lines: status.append("empty_label")
                for number,line in enumerate(label_lines,1):
                    values=line.split()
                    try:
                        coords=[float(value) for value in values[1:]]
                        if len(values)<7 or len(coords)%2 or any(value<0 or value>1 for value in coords): status.append(f"invalid_polygon_line_{number}")
                    except ValueError: status.append(f"non_numeric_line_{number}")
            digest=hashlib.sha256(path.read_bytes()).hexdigest(); duplicate_of=hashes.get(digest,""); hashes.setdefault(digest,relative.as_posix())
            if duplicate_of: status.append("duplicate")
            rows.append({"relative_path":relative.as_posix(),"class_name":class_dir.name,"status":";".join(status) or "ok","duplicate_of":duplicate_of})
    found=sorted({row["class_name"] for row in rows}); summary={"images":len(rows),"classes":found,"expected_classes":SPECIES,
      "status_counts":dict(Counter(row["status"] for row in rows)),"valid":found==SPECIES and all(row["status"]=="ok" for row in rows)}
    output=Path(args.output); output.mkdir(parents=True,exist_ok=True)
    with (output/"annotation_audit.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
    (output/"annotation_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8"); print(json.dumps(summary,indent=2))


if __name__ == "__main__": main()
