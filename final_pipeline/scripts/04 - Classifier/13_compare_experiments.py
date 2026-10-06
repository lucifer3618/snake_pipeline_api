"""Combine CV summaries from whole, GT-ROI and predicted-ROI experiments."""
import argparse
import csv
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--inputs",nargs="+",required=True,help="variant=summary.csv")
    parser.add_argument("--experiment",required=True); parser.add_argument("--output",required=True); args=parser.parse_args(); rows=[]
    for item in args.inputs:
        variant,path=item.split("=",1)
        with open(path,newline="",encoding="utf-8") as handle:
            match=next((row for row in csv.DictReader(handle) if row.get("experiment",row["architecture"])==args.experiment),None)
        if match is None: raise SystemExit(f"{args.experiment} not found in {path}")
        rows.append({"input_variant":variant,**match})
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
    print(f"Wrote {output}")


if __name__ == "__main__": main()
