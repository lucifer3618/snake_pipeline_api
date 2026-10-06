"""Select safety thresholds using only the dedicated calibration predictions."""
import argparse
import csv
import json
from itertools import product
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--predictions", required=True); parser.add_argument("--output", required=True)
    parser.add_argument("--minimum-coverage", type=float, default=.50); args=parser.parse_args()
    with open(args.predictions, newline="", encoding="utf-8") as handle: rows=list(csv.DictReader(handle))
    best=None
    # Include fallback-detector scores; calibration decides whether their added
    # coverage is sufficiently reliable rather than rejecting them a priori.
    grids=product([.10,.15,.20,.25,.35,.45], [.4,.5,.6,.7,.8], [.05,.1,.15,.2], [.4,.6,.8,1.0], [.55,.65,.75,.85])
    for detector, confidence, margin, agreement, entropy in grids:
        accepted=[row for row in rows if float(row["detector_confidence"])>=detector and float(row["species_confidence"])>=confidence
          and float(row["species_margin"])>=margin and float(row["agreement"])>=agreement
          and float(row["normalized_entropy"])<=entropy and row["venom_consistent"].lower() == "true"]
        coverage=len(accepted)/max(1,len(rows))
        if coverage < args.minimum_coverage: continue
        accuracy=sum(row["true_index"]==row["predicted_index"] for row in accepted)/len(accepted)
        candidate={"detector_confidence":detector,"species_confidence":confidence,"species_margin":margin,
                   "agreement":agreement,"maximum_entropy":entropy,"calibration_coverage":coverage,"calibration_accepted_accuracy":accuracy}
        if best is None or (accuracy,coverage)>(best["calibration_accepted_accuracy"],best["calibration_coverage"]): best=candidate
    if best is None: raise SystemExit("No setting meets minimum coverage")
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(best,indent=2),encoding="utf-8")
    print(json.dumps(best,indent=2))


if __name__ == "__main__": main()
