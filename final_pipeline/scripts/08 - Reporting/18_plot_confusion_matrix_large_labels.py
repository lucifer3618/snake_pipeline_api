"""Generate the final test confusion matrix with enlarged full class names."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


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

DISPLAY = {
    "bungarus_caeruleus": "Bungarus\ncaeruleus",
    "coelognathus_helena": "Coelognathus\nhelena",
    "craspedocephalus_trigonocephalus": "Craspedocephalus\ntrigonocephalus",
    "daboia_russelii": "Daboia\nrusselii",
    "hypnale_hypnale": "Hypnale\nhypnale",
    "lycodon_aulicus": "Lycodon\naulicus",
    "naja_naja": "Naja\nnaja",
    "oligodon_arnensis": "Oligodon\narnensis",
}

WIDTH, HEIGHT = 3200, 2700
INK = "#171A1E"
MUTED = "#8D8D8D"
OUTLINE = "#30343A"


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confusion-matrix", required=True)
    parser.add_argument("--output", default="outputs/thesis_figures")
    return parser.parse_args()


def font(size: int, *, bold: bool = False, italic: bool = False):
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


def load_matrix(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    if rows[0][1:] != SPECIES or [row[0] for row in rows[1:]] != SPECIES:
        raise ValueError("Unexpected species order in confusion matrix")
    return [[int(value) for value in row[1:]] for row in rows[1:]]


def blue(value: float):
    value = max(0.0, min(1.0, value))
    start = (247, 250, 253)
    end = (8, 61, 120)
    return tuple(round(a + (b - a) * value) for a, b in zip(start, end))


def vertical_text(image, text, centre, size):
    layer = Image.new("RGBA", (720, 100), (255, 255, 255, 0))
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.text((360, 50), text, font=font(size), fill=INK, anchor="mm")
    layer = layer.rotate(90, expand=True)
    image.paste(
        layer,
        (round(centre[0] - layer.width / 2), round(centre[1] - layer.height / 2)),
        layer,
    )


def create(matrix, output: Path):
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)

    left, top, cell = 500, 300, 270
    matrix_size = cell * 8

    draw.text(
        (left + matrix_size / 2, 38),
        "Ensemble Confusion Matrix – Test Set",
        font=font(48, bold=True),
        fill=INK,
        anchor="ma",
    )
    draw.text(
        (left + matrix_size / 2, 105),
        "219 classified images (3 detector failures excluded) · Accuracy 86.3%",
        font=font(38),
        fill=INK,
        anchor="ma",
    )

    for row, (species, values) in enumerate(zip(SPECIES, matrix)):
        y = top + row * cell
        total = sum(values)
        draw.multiline_text(
            (left - 30, y + cell / 2),
            DISPLAY[species],
            font=font(42, italic=True),
            fill=INK,
            anchor="rm",
            align="right",
            spacing=4,
        )
        for column, count in enumerate(values):
            percentage = count / total if total else 0.0
            x = left + column * cell
            draw.rectangle(
                (x, y, x + cell, y + cell),
                fill=blue(percentage),
                outline="white",
                width=4,
            )
            if count == 0:
                draw.text(
                    (x + cell / 2, y + cell / 2),
                    "0",
                    font=font(30),
                    fill=MUTED,
                    anchor="mm",
                )
                continue
            text_colour = "white" if percentage >= 0.52 else INK
            draw.multiline_text(
                (x + cell / 2, y + cell / 2),
                f"{count}\n{percentage * 100:.1f}%",
                font=font(38, bold=percentage >= 0.52),
                fill=text_colour,
                anchor="mm",
                align="center",
                spacing=5,
            )

    draw.rectangle(
        (left, top, left + matrix_size, top + matrix_size),
        outline=OUTLINE,
        width=3,
    )

    label_y = top + matrix_size + 28
    for column, species in enumerate(SPECIES):
        x = left + column * cell + cell / 2
        label_size = 31 if species in {
            "coelognathus_helena",
            "craspedocephalus_trigonocephalus",
        } else 36
        draw.multiline_text(
            (x, label_y),
            DISPLAY[species],
            font=font(label_size, italic=True),
            fill=INK,
            anchor="ma",
            align="center",
            spacing=3,
        )

    draw.text(
        (left + matrix_size / 2, HEIGHT - 28),
        "Predicted species",
        font=font(42),
        fill=INK,
        anchor="ms",
    )
    vertical_text(image, "True species", (65, top + matrix_size / 2), 42)

    bar_x, bar_width = left + matrix_size + 72, 72
    for pixel in range(matrix_size):
        value = 1.0 - pixel / (matrix_size - 1)
        draw.line(
            (bar_x, top + pixel, bar_x + bar_width, top + pixel),
            fill=blue(value),
            width=1,
        )
    draw.rectangle(
        (bar_x, top, bar_x + bar_width, top + matrix_size),
        outline=OUTLINE,
        width=2,
    )
    for percentage in (0, 20, 40, 60, 80, 100):
        y = top + matrix_size * (1 - percentage / 100)
        draw.line((bar_x + bar_width, y, bar_x + bar_width + 14, y), fill=INK, width=2)
        draw.text(
            (bar_x + bar_width + 25, y),
            str(percentage),
            font=font(29),
            fill=INK,
            anchor="lm",
        )
    vertical_text(
        image,
        "Row-normalized (%)",
        (bar_x + 205, top + matrix_size / 2),
        32,
    )

    output.mkdir(parents=True, exist_ok=True)
    path = output / "final_test_confusion_matrix_large_labels.png"
    image.save(path, dpi=(300, 300), optimize=True)
    return path


def main():
    args = arguments()
    result = create(load_matrix(Path(args.confusion_matrix)), Path(args.output))
    print(result)


if __name__ == "__main__":
    main()
