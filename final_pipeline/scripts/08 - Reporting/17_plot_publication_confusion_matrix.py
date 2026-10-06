"""Create a compact, publication-ready row-normalized confusion matrix."""
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

WIDTH, HEIGHT = 2300, 1800
BACKGROUND = "#FFFFFF"
INK = "#20252B"
MUTED = "#59636E"
GRID = "#FFFFFF"
OUTLINE = "#8C98A4"


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
    header = rows[0][1:]
    labels = [row[0] for row in rows[1:]]
    if header != SPECIES or labels != SPECIES:
        raise ValueError("Unexpected species order in confusion matrix")
    return [[int(value) for value in row[1:]] for row in rows[1:]]


def blue(value: float):
    """Perceptually clear light-to-dark blue suitable for printing."""
    value = max(0.0, min(1.0, value)) ** 0.72
    start = (247, 250, 252)
    end = (0, 83, 138)
    return tuple(round(a + (b - a) * value) for a, b in zip(start, end))


def draw_vertical_text(image: Image.Image, text: str, xy: tuple[int, int], size: int):
    layer = Image.new("RGBA", (520, 80), (255, 255, 255, 0))
    layer_draw = ImageDraw.Draw(layer)
    layer_draw.text((260, 40), text, font=font(size), fill=INK, anchor="mm")
    layer = layer.rotate(90, expand=True)
    image.paste(layer, (xy[0] - layer.width // 2, xy[1] - layer.height // 2), layer)


def create_figure(matrix, output: Path):
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    left, top, cell = 505, 270, 170
    matrix_size = cell * len(SPECIES)

    draw.text(
        (left + matrix_size / 2, 64),
        "Predicted species",
        font=font(38, bold=True),
        fill=INK,
        anchor="ma",
    )

    for column, species in enumerate(SPECIES):
        x = left + column * cell + cell / 2
        genus, species_name = SHORT[species].split(" ", 1)
        draw.multiline_text(
            (x, top - 90),
            f"{genus}\n{species_name}",
            font=font(27, italic=True),
            fill=INK,
            anchor="mm",
            align="center",
            spacing=3,
        )

    for row, (species, values) in enumerate(zip(SPECIES, matrix)):
        y = top + row * cell
        support = sum(values)
        draw.text(
            (left - 28, y + cell / 2),
            f"{SHORT[species]}  (n={support})",
            font=font(28, italic=True),
            fill=INK,
            anchor="rm",
        )

        for column, count in enumerate(values):
            proportion = count / support if support else 0.0
            x = left + column * cell
            draw.rectangle(
                (x, y, x + cell, y + cell),
                fill=blue(proportion),
                outline=GRID,
                width=4,
            )
            if count == 0:
                continue

            text_colour = "#FFFFFF" if proportion >= 0.48 else INK
            draw.text(
                (x + cell / 2, y + cell / 2 - 20),
                f"{proportion * 100:.1f}%",
                font=font(29, bold=True),
                fill=text_colour,
                anchor="mm",
            )
            draw.text(
                (x + cell / 2, y + cell / 2 + 25),
                f"({count})",
                font=font(24),
                fill=text_colour,
                anchor="mm",
            )

    draw.rectangle(
        (left, top, left + matrix_size, top + matrix_size),
        outline=OUTLINE,
        width=3,
    )
    draw_vertical_text(image, "True species", (75, top + matrix_size // 2), 38)

    colourbar_x = left + matrix_size + 92
    colourbar_width = 46
    for pixel in range(matrix_size):
        value = 1.0 - pixel / max(1, matrix_size - 1)
        draw.line(
            (colourbar_x, top + pixel, colourbar_x + colourbar_width, top + pixel),
            fill=blue(value),
            width=1,
        )
    draw.rectangle(
        (colourbar_x, top, colourbar_x + colourbar_width, top + matrix_size),
        outline=OUTLINE,
        width=2,
    )
    for percentage in (0, 20, 40, 60, 80, 100):
        y = top + matrix_size * (1 - percentage / 100)
        draw.line(
            (colourbar_x + colourbar_width, y, colourbar_x + colourbar_width + 12, y),
            fill=INK,
            width=2,
        )
        draw.text(
            (colourbar_x + colourbar_width + 22, y),
            f"{percentage}%",
            font=font(23),
            fill=INK,
            anchor="lm",
        )
    draw_vertical_text(
        image,
        "Percentage of true class",
        (colourbar_x + 165, top + matrix_size // 2),
        29,
    )

    draw.text(
        (left + matrix_size / 2, top + matrix_size + 58),
        "Non-zero cells show row percentage with image count in parentheses.",
        font=font(26),
        fill=MUTED,
        anchor="ma",
    )

    output.mkdir(parents=True, exist_ok=True)
    path = output / "final_test_confusion_matrix_publication.png"
    image.save(path, dpi=(300, 300), optimize=True)
    return path


def main():
    args = arguments()
    path = create_figure(load_matrix(Path(args.confusion_matrix)), Path(args.output))
    print(path)


if __name__ == "__main__":
    main()
