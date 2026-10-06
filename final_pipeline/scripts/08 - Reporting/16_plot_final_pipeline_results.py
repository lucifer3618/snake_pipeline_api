"""Generate thesis-ready final-pipeline figures from recorded test outputs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH, HEIGHT = 2100, 1500
INK = "#202020"
MUTED = "#555555"
BLUE = "#0072B2"
BLUE_DARK = "#004B75"
BLUE_LIGHT = "#E7F2F8"
GREEN = "#18864B"
GREEN_LIGHT = "#E6F4EB"
ORANGE = "#D55E00"
ORANGE_LIGHT = "#FBEDE5"
RED = "#B33A3A"
RED_LIGHT = "#F8E8E8"
GRID = "#D8D8D8"

SPECIES = [
    "bungarus_caeruleus",
    "coelognathus_helena",
    "craspedocephalus_trigonocephalus",
    "daboia_russelii",
    "hypnale_hypnale",
    "lycodon_aulicus",
    "naja_naja",
    "oligodon_arnensis",
]
SHORT = {
    "bungarus_caeruleus": "B. caeruleus",
    "coelognathus_helena": "C. helena",
    "craspedocephalus_trigonocephalus": "C. trigonocephalus",
    "daboia_russelii": "D. russelii",
    "hypnale_hypnale": "H. hypnale",
    "lycodon_aulicus": "L. aulicus",
    "naja_naja": "N. naja",
    "oligodon_arnensis": "O. arnensis",
}


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confusion-matrix", required=True)
    parser.add_argument("--classification-report", required=True)
    parser.add_argument("--output", default="outputs/thesis_figures")
    return parser.parse_args()


def font(size: int, bold: bool = False, italic: bool = False):
    if bold and italic:
        filename = "arialbi.ttf"
    elif bold:
        filename = "arialbd.ttf"
    elif italic:
        filename = "ariali.ttf"
    else:
        filename = "arial.ttf"
    path = Path("C:/Windows/Fonts") / filename
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def title(draw, text):
    draw.text((WIDTH / 2, 64), text, font=font(54, True), fill=INK, anchor="ma")


def box(draw, xy, heading, detail="", fill=BLUE_LIGHT, stroke=BLUE_DARK,
        heading_size=34, detail_size=29):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=20, fill=fill, outline=stroke, width=4)
    center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
    if detail:
        draw.text((center_x, center_y - 23), heading, font=font(heading_size, True),
                  fill=INK, anchor="mm")
        draw.text((center_x, center_y + 30), detail, font=font(detail_size),
                  fill=MUTED, anchor="mm")
    else:
        draw.text((center_x, center_y), heading, font=font(heading_size, True),
                  fill=INK, anchor="mm")


def arrow(draw, start, end, fill=MUTED, width=5):
    draw.line((start, end), fill=fill, width=width)
    x, y = end
    if abs(end[1] - start[1]) >= abs(end[0] - start[0]):
        points = [(x, y), (x - 13, y - 22), (x + 13, y - 22)] if y >= start[1] else [(x, y), (x - 13, y + 22), (x + 13, y + 22)]
    else:
        points = [(x, y), (x - 22, y - 13), (x - 22, y + 13)] if x >= start[0] else [(x, y), (x + 22, y - 13), (x + 22, y + 13)]
    draw.polygon(points, fill=fill)


def save(image, output: Path, name: str):
    png = output / f"{name}.png"
    pdf = output / f"{name}.pdf"
    image.save(png, dpi=(300, 300))
    image.convert("RGB").save(pdf, "PDF", resolution=300)
    return png, pdf


def safety_gate_figure(output: Path):
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    title(draw, "Calibrated safety-gate decision conditions")
    box(draw, (660, 135, 1440, 265), "Detector and five-model ensemble outputs")
    arrow(draw, (1050, 265), (1050, 330))

    draw.rounded_rectangle((260, 330, 1840, 1055), radius=24, fill="#F7FAFC", outline=BLUE_DARK, width=4)
    draw.text((1050, 370), "All conditions required", font=font(38, True), fill=INK, anchor="ma")
    conditions = [
        ("Detector confidence", "≥ 0.35"),
        ("Species confidence", "≥ 0.40"),
        ("Prediction margin", "≥ 0.05"),
        ("Fold agreement", "= 1.00"),
        ("Normalized entropy", "≤ 0.55"),
        ("Species–venom consistency", "Required"),
    ]
    positions = [
        (340, 445, 980, 600), (1120, 445, 1760, 600),
        (340, 635, 980, 790), (1120, 635, 1760, 790),
        (340, 825, 980, 980), (1120, 825, 1760, 980),
    ]
    for position, (heading, detail) in zip(positions, conditions):
        box(draw, position, heading, detail)
    arrow(draw, (1050, 1055), (1050, 1120))
    box(draw, (690, 1120, 1410, 1235), "Are all conditions satisfied?", fill="#F1F1F1", stroke=MUTED)
    draw.line((1050, 1235, 1050, 1280), fill=MUTED, width=5)
    draw.line((1050, 1280, 590, 1280), fill=MUTED, width=5)
    draw.line((1050, 1280, 1510, 1280), fill=MUTED, width=5)
    arrow(draw, (590, 1280), (590, 1320), fill=GREEN)
    arrow(draw, (1510, 1280), (1510, 1320), fill=ORANGE)
    draw.text((760, 1260), "Yes", font=font(28, True), fill=GREEN, anchor="mm")
    draw.text((1340, 1260), "No", font=font(28, True), fill=ORANGE, anchor="mm")
    box(draw, (330, 1320, 850, 1440), "ACCEPT", "Return species prediction", GREEN_LIGHT, GREEN)
    box(draw, (1250, 1320, 1770, 1440), "WITHHOLD", "Return uncertainty warning", ORANGE_LIGHT, ORANGE)
    return save(image, output, "safety_gate_conditions")


def test_outcome_figure(output: Path):
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    title(draw, "Final test-set flow through the pipeline and safety gate")

    box(draw, (730, 130, 1370, 255), "Test images", "222")
    draw.line((1050, 255, 1050, 325), fill=MUTED, width=5)
    draw.line((1050, 325, 465, 325), fill=MUTED, width=5)
    draw.line((1050, 325, 1425, 325), fill=MUTED, width=5)
    arrow(draw, (465, 325), (465, 380), RED)
    arrow(draw, (1425, 325), (1425, 380), BLUE_DARK)
    box(draw, (190, 380, 740, 535), "Detector failure", "3 images (1.35%)", RED_LIGHT, RED)
    box(draw, (1110, 380, 1740, 535), "Successfully classified", "219 images (98.65%)")

    draw.line((1425, 535, 1425, 620), fill=MUTED, width=5)
    draw.line((1425, 620, 1040, 620), fill=MUTED, width=5)
    draw.line((1425, 620, 1810, 620), fill=MUTED, width=5)
    arrow(draw, (1040, 620), (1040, 675), GREEN)
    arrow(draw, (1810, 620), (1810, 675), ORANGE)
    box(draw, (720, 675, 1320, 830), "Accepted", "146 images (65.77% of test)", GREEN_LIGHT, GREEN)
    box(draw, (1500, 675, 2070, 830), "Withheld", "73 images", ORANGE_LIGHT, ORANGE)

    draw.line((1040, 830, 1040, 925), fill=MUTED, width=5)
    draw.line((1040, 925, 750, 925), fill=MUTED, width=5)
    draw.line((1040, 925, 1280, 925), fill=MUTED, width=5)
    arrow(draw, (750, 925), (750, 980), GREEN)
    arrow(draw, (1280, 925), (1280, 980), RED)
    box(draw, (510, 980, 990, 1125), "Correct accepted", "143 (97.95%)", GREEN_LIGHT, GREEN)
    box(draw, (1040, 980, 1520, 1125), "Incorrect accepted", "3 (2.05%)", RED_LIGHT, RED)

    draw.line((1810, 830, 1810, 925), fill=MUTED, width=5)
    draw.line((1810, 925, 1635, 925), fill=MUTED, width=5)
    draw.line((1810, 925, 1980, 925), fill=MUTED, width=5)
    arrow(draw, (1635, 925), (1635, 980), ORANGE)
    arrow(draw, (1980, 925), (1980, 980), ORANGE)
    box(draw, (1530, 980, 1770, 1125), "Correct", "46", ORANGE_LIGHT, ORANGE, 30, 28)
    box(draw, (1840, 980, 2080, 1125), "Incorrect", "27", ORANGE_LIGHT, ORANGE, 30, 28)

    draw.rounded_rectangle((280, 1230, 1820, 1410), radius=18, fill="#F7FAFC", outline=GRID, width=3)
    draw.text((1050, 1280), "Safety outcome", font=font(35, True), fill=INK, anchor="ma")
    draw.text((1050, 1345), "27 of 30 detected-image errors were withheld (90.00% error-detection rate).",
              font=font(31), fill=INK, anchor="ma")
    return save(image, output, "final_test_outcome_flow")


def load_confusion(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    header = rows[0][1:]
    matrix = [[int(value) for value in row[1:]] for row in rows[1:]]
    if header != SPECIES or [row[0] for row in rows[1:]] != SPECIES:
        raise ValueError("Unexpected species order in confusion matrix")
    return matrix


def blend_blue(value: float):
    start = (245, 249, 252)
    end = (0, 90, 145)
    return tuple(round(a + (b - a) * value) for a, b in zip(start, end))


def confusion_figure(matrix, output: Path):
    image = Image.new("RGB", (WIDTH, 1900), "white")
    draw = ImageDraw.Draw(image)
    draw.text((WIDTH / 2, 56), "Normalized confusion matrix on classified test images",
              font=font(52, True), fill=INK, anchor="ma")
    left, top, cell = 470, 300, 174
    draw.text((left + 4 * cell, 135), "Predicted species", font=font(38), fill=INK, anchor="ma")

    for column, species in enumerate(SPECIES):
        x = left + column * cell + cell / 2
        label = SHORT[species].replace(" ", "\n", 1)
        draw.multiline_text((x, top - 100), label, font=font(25, italic=True), fill=INK,
                            anchor="mm", align="center", spacing=3)

    for row, (species, values) in enumerate(zip(SPECIES, matrix)):
        y = top + row * cell
        total = sum(values)
        draw.text((left - 30, y + cell / 2), SHORT[species], font=font(27, italic=True),
                  fill=INK, anchor="rm")
        for column, count in enumerate(values):
            percentage = count / total if total else 0
            x = left + column * cell
            fill = blend_blue(percentage)
            draw.rectangle((x, y, x + cell, y + cell), fill=fill, outline="white", width=4)
            text_fill = "white" if percentage >= .48 else INK
            label = "0" if count == 0 else f"{percentage * 100:.1f}%"
            draw.text((x + cell / 2, y + cell / 2 - 12), label, font=font(28, True),
                      fill=text_fill, anchor="mm")
            if count:
                draw.text((x + cell / 2, y + cell / 2 + 30), f"n={count}", font=font(22),
                          fill=text_fill, anchor="mm")

    axis_image = Image.new("RGBA", (650, 70), (255, 255, 255, 0))
    axis_draw = ImageDraw.Draw(axis_image)
    axis_draw.text((325, 35), "True species", font=font(38), fill=INK, anchor="mm")
    axis_image = axis_image.rotate(90, expand=True)
    image.paste(axis_image, (55, top + round((8 * cell - axis_image.height) / 2)), axis_image)

    legend_x, legend_y, legend_width = 680, 1760, 740
    for index in range(100):
        value = index / 99
        x1 = legend_x + index * legend_width / 100
        x2 = legend_x + (index + 1) * legend_width / 100
        draw.rectangle((x1, legend_y, x2 + 1, legend_y + 28), fill=blend_blue(value))
    draw.text((legend_x, legend_y + 45), "0%", font=font(24), fill=INK, anchor="la")
    draw.text((legend_x + legend_width, legend_y + 45), "100%", font=font(24), fill=INK, anchor="ra")
    draw.text((WIDTH / 2, 1860), "Rows are normalized by true-species support; cell counts are shown as n.",
              font=font(26), fill=MUTED, anchor="ma")
    return save(image, output, "final_test_confusion_matrix_normalized")


def class_f1_figure(report, output: Path):
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    title(draw, "Class-wise F1 scores on classified test images")
    left, right, top, bottom = 580, 1900, 190, 1320
    row_height = (bottom - top) / len(SPECIES)

    for value in [0, .2, .4, .6, .8, 1.0]:
        x = left + value * (right - left)
        draw.line((x, top, x, bottom), fill=GRID, width=2)
        draw.text((x, bottom + 30), f"{value:.1f}", font=font(27), fill=INK, anchor="ma")
    for index, species in enumerate(SPECIES):
        score = float(report[species]["f1-score"])
        y = top + index * row_height + row_height / 2
        draw.text((left - 32, y), SHORT[species], font=font(31, italic=True), fill=INK, anchor="rm")
        bar_height = 72
        bar_color = ORANGE if species == "naja_naja" else (GREEN if score == 1.0 else BLUE)
        draw.rounded_rectangle((left, y - bar_height / 2, left + score * (right - left), y + bar_height / 2),
                               radius=10, fill=bar_color)
        draw.text((left + score * (right - left) + 20, y), f"{score:.3f}",
                  font=font(29, True), fill=INK, anchor="lm")
    draw.line((left, bottom, right, bottom), fill=INK, width=4)
    draw.text(((left + right) / 2, 1430), "F1 score", font=font(38), fill=INK, anchor="mm")
    return save(image, output, "final_test_classwise_f1")


def write_tables(output: Path):
    final_rows = [
        ("Test images", "222", "All test images"),
        ("Classified images", "219", "Successful detector output"),
        ("Technical detector coverage", "98.65%", "219/222"),
        ("Detected-image accuracy", "86.30%", "189/219"),
        ("Detected-image macro F1", "86.50%", "219 classified images"),
        ("Automated end-to-end accuracy", "85.14%", "189/222"),
        ("Gate coverage", "65.77%", "146/222"),
        ("Accepted accuracy", "97.95%", "143/146"),
        ("Error-detection rate", "90.00%", "27/30 detected-image errors"),
        ("Species–venom contradictions", "6", "Classified images"),
        ("Mean ensemble-classification latency", "39.80 ms", "Classifier ensemble only"),
    ]
    with (output / "final_test_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Metric", "Result", "Scope or denominator"))
        writer.writerows(final_rows)

    calibration_rows = [
        ("Calibration images", "223"),
        ("Successfully classified", "222"),
        ("Accepted predictions", "143"),
        ("Coverage among classified images", "64.41%"),
        ("Accuracy among accepted predictions", "97.20%"),
    ]
    with (output / "calibration_results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Metric", "Result"))
        writer.writerows(calibration_rows)


def main():
    args = arguments()
    output = Path(args.output)
    if not output.is_absolute():
        output = Path(__file__).resolve().parents[2] / output
    output.mkdir(parents=True, exist_ok=True)
    matrix = load_confusion(Path(args.confusion_matrix))
    report = json.loads(Path(args.classification_report).read_text(encoding="utf-8"))
    safety_gate_figure(output)
    test_outcome_figure(output)
    confusion_figure(matrix, output)
    class_f1_figure(report, output)
    write_tables(output)
    print(f"Saved final evaluation figures and tables to {output.resolve()}")


if __name__ == "__main__":
    main()
