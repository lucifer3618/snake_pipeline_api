"""Evaluate the five-fold dual-head ensemble on calibration or untouched test data."""
import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path
import torch
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from snake_pipeline.config import SPECIES
from snake_pipeline.ensemble import FoldEnsemble
from snake_pipeline.safety import gate


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--data", required=True); parser.add_argument("--checkpoints", nargs="+", required=True)
    parser.add_argument("--audit", required=True); parser.add_argument("--split", choices=["calibration", "test"], required=True)
    parser.add_argument("--thresholds"); parser.add_argument("--output", required=True); parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args(); device = torch.device(args.device if not args.device.startswith("cuda") or torch.cuda.is_available() else "cpu")
    models = FoldEnsemble(args.checkpoints, device)
    dataset = ImageFolder(args.data, models.transform);
    if dataset.classes != SPECIES: raise ValueError(f"Class order mismatch: {dataset.classes}")
    thresholds = json.loads(Path(args.thresholds).read_text()) if args.thresholds else None
    audit = {}
    with open(args.audit, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["variant"] == "predicted_roi" and row["split"] == args.split and row["fold"] == "0": audit[row["image_id"]] = row
    rows = []
    for index, (image, label) in enumerate(DataLoader(dataset, batch_size=1, shuffle=False)):
        image=image.to(device)
        if device.type == "cuda": torch.cuda.synchronize()
        started=time.perf_counter(); result = models.predict(image)
        if device.type == "cuda": torch.cuda.synchronize()
        result["ensemble_latency_ms"]=(time.perf_counter()-started)*1000
        image_id = Path(dataset.samples[index][0]).stem; item = audit.get(image_id, {})
        result.update({"image_id": image_id, "true_index": int(label), "true_species": SPECIES[int(label)],
                       "detector_confidence": float(item.get("detector_confidence") or 0),
                       "detection_stage": item.get("detection_stage") or "primary"})
        decision, reasons = gate(result, thresholds); result.update({"decision": decision, "reasons": ";".join(reasons)})
        result["member_votes"] = json.dumps(result["member_votes"]); rows.append(result)
    successful = len(rows); total = sum(1 for row in audit.values()); accepted = [row for row in rows if row["decision"] == "ACCEPT"]
    correct = sum(row["true_index"] == row["predicted_index"] for row in rows)
    accepted_correct = sum(row["true_index"] == row["predicted_index"] for row in accepted)
    wrong=[row for row in rows if row["true_index"] != row["predicted_index"]]
    wrong_withheld=sum(row["decision"] == "WITHHOLD" for row in wrong)
    metrics = {"split": args.split, "total_manifest_images": total, "classified": successful,
               "detector_coverage": successful/max(1,total), "end_to_end_accuracy": correct/max(1,total),
               "gate_coverage": len(accepted)/max(1,total), "accepted_accuracy": accepted_correct/max(1,len(accepted)),
               "error_detection_rate": wrong_withheld/max(1,len(wrong)),
               "mean_ensemble_latency_ms": sum(row["ensemble_latency_ms"] for row in rows)/max(1,len(rows)),
               "contradictions": sum(not row["venom_consistent"] for row in rows),
               "classified_by_detection_stage": dict(Counter(row["detection_stage"] for row in rows)),
               "accepted_by_detection_stage": dict(Counter(row["detection_stage"] for row in accepted))}
    output = Path(args.output); output.mkdir(parents=True, exist_ok=True)
    with (output/"predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer=csv.DictWriter(handle, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
    (output/"metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8"); print(json.dumps(metrics, indent=2))
    truth=[row["true_index"] for row in rows]; predicted=[row["predicted_index"] for row in rows]
    (output/"classification_report.json").write_text(json.dumps(classification_report(truth,predicted,
        labels=range(len(SPECIES)),target_names=SPECIES,output_dict=True,zero_division=0),indent=2),encoding="utf-8")
    with (output/"confusion_matrix.csv").open("w",newline="",encoding="utf-8") as handle:
        writer=csv.writer(handle); writer.writerow(["true/predicted",*SPECIES])
        for name,line in zip(SPECIES,confusion_matrix(truth,predicted,labels=range(len(SPECIES)))): writer.writerow([name,*line])


if __name__ == "__main__": main()
