"""Create the thesis classifier accuracy-efficiency scatter plot.

Uses Pillow plus a parallel SVG export so it does not depend on Matplotlib.
"""
from __future__ import annotations

from html import escape
from math import cos, pi, sin
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


MODELS = [
    ("MobileNetV2", 2.234120, 0.780222, 0.020210),
    ("MobileNetV2-SE", 2.440280, 0.764527, 0.021595),
    ("MobileNetV2-CBAM", 2.440378, 0.775074, 0.022073),
    ("EfficientNet-B0", 4.017796, 0.801713, 0.039498),
    ("MobileViT-XS", 1.935928, 0.816953, 0.024190),
]

WIDTH, HEIGHT = 2160, 1440
LEFT, RIGHT, TOP, BOTTOM = 285, 120, 190, 245
PLOT_RIGHT, PLOT_BOTTOM = WIDTH - RIGHT, HEIGHT - BOTTOM
X_MIN, X_MAX = 1.70, 4.25
Y_MIN, Y_MAX = .72, .86

BLUE = "#0072B2"
BLUE_EDGE = "#004B75"
ORANGE = "#D55E00"
ORANGE_EDGE = "#7A2E00"
INK = "#202020"
MID = "#555555"
GRID = "#D8D8D8"


def font(size: int, bold: bool = False):
    filename = "arialbd.ttf" if bold else "arial.ttf"
    path = Path("C:/Windows/Fonts") / filename
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def x_position(value: float) -> float:
    return LEFT + (value - X_MIN) / (X_MAX - X_MIN) * (PLOT_RIGHT - LEFT)


def y_position(value: float) -> float:
    return PLOT_BOTTOM - (value - Y_MIN) / (Y_MAX - Y_MIN) * (PLOT_BOTTOM - TOP)


def star_points(x: float, y: float, outer: float, inner: float):
    points = []
    for index in range(10):
        angle = -pi / 2 + index * pi / 5
        radius = outer if index % 2 == 0 else inner
        points.append((x + cos(angle) * radius, y + sin(angle) * radius))
    return points


def centered(draw: ImageDraw.ImageDraw, xy, text: str, text_font, fill=INK):
    draw.text(xy, text, font=text_font, fill=fill, anchor="mm")


def make_png_and_pdf(output: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)
    title_font, axis_font = font(48, True), font(39)
    tick_font, label_font, note_font = font(31), font(31), font(27)
    selected_font = font(31, True)

    centered(draw, (WIDTH / 2, 72), "Classifier accuracy–efficiency trade-off", title_font)

    y_ticks = [.72, .74, .76, .78, .80, .82, .84, .86]
    for value in y_ticks:
        y = y_position(value)
        draw.line((LEFT, y, PLOT_RIGHT, y), fill=GRID, width=2)
        draw.text((LEFT - 25, y), f"{value:.2f}", font=tick_font, fill=INK, anchor="rm")
    for value in [2.0, 2.5, 3.0, 3.5, 4.0]:
        x = x_position(value)
        draw.line((x, PLOT_BOTTOM, x, PLOT_BOTTOM + 12), fill=INK, width=3)
        draw.text((x, PLOT_BOTTOM + 28), f"{value:.1f}", font=tick_font, fill=INK, anchor="ma")

    draw.line((LEFT, TOP, LEFT, PLOT_BOTTOM), fill=INK, width=4)
    draw.line((LEFT, PLOT_BOTTOM, PLOT_RIGHT, PLOT_BOTTOM), fill=INK, width=4)
    centered(draw, (WIDTH / 2, HEIGHT - 105), "Model parameters (millions)", axis_font)

    y_label = Image.new("RGBA", (720, 75), (255, 255, 255, 0))
    y_draw = ImageDraw.Draw(y_label)
    centered(y_draw, (360, 37), "Mean five-fold macro F1", axis_font)
    y_label = y_label.rotate(90, expand=True)
    image.paste(y_label, (55, round((HEIGHT - y_label.height) / 2)), y_label)
    draw = ImageDraw.Draw(image)

    label_offsets = {
        "MobileViT-XS": (32, -72, "la"),
        "MobileNetV2": (-28, -66, "ra"),
        "MobileNetV2-SE": (30, 25, "lt"),
        "MobileNetV2-CBAM": (30, -62, "la"),
        "EfficientNet-B0": (-30, -65, "ra"),
    }

    for name, parameters, mean_f1, std_f1 in MODELS:
        x, y = x_position(parameters), y_position(mean_f1)
        y_top, y_bottom = y_position(mean_f1 + std_f1), y_position(mean_f1 - std_f1)
        draw.line((x, y_top, x, y_bottom), fill=MID, width=4)
        draw.line((x - 14, y_top, x + 14, y_top), fill=MID, width=4)
        draw.line((x - 14, y_bottom, x + 14, y_bottom), fill=MID, width=4)
        selected = name == "MobileViT-XS"
        if selected:
            draw.polygon(star_points(x, y, 26, 12), fill=ORANGE, outline=ORANGE_EDGE)
        else:
            draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill=BLUE, outline=BLUE_EDGE, width=3)
        dx, dy, anchor = label_offsets[name]
        label = "MobileViT-XS (selected)" if selected else name
        draw.text((x + dx, y + dy), label, font=selected_font if selected else label_font,
                  fill=INK, anchor=anchor)

    draw.text((LEFT + 15, PLOT_BOTTOM - 22),
              "Error bars show sample standard deviation across five folds.",
              font=note_font, fill=MID, anchor="ls")
    image.save(output.with_suffix(".png"), dpi=(300, 300))
    image.save(output.with_suffix(".pdf"), "PDF", resolution=300)


def make_svg(output: Path) -> None:
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{WIDTH/2}" y="82" text-anchor="middle" font-family="Arial" font-size="48" font-weight="700" fill="{INK}">Classifier accuracy–efficiency trade-off</text>',
    ]
    for value in [.72, .74, .76, .78, .80, .82, .84, .86]:
        y = y_position(value)
        elements += [
            f'<line x1="{LEFT}" y1="{y:.1f}" x2="{PLOT_RIGHT}" y2="{y:.1f}" stroke="{GRID}" stroke-width="2"/>',
            f'<text x="{LEFT-25}" y="{y+10:.1f}" text-anchor="end" font-family="Arial" font-size="31" fill="{INK}">{value:.2f}</text>',
        ]
    for value in [2.0, 2.5, 3.0, 3.5, 4.0]:
        x = x_position(value)
        elements += [
            f'<line x1="{x:.1f}" y1="{PLOT_BOTTOM}" x2="{x:.1f}" y2="{PLOT_BOTTOM+12}" stroke="{INK}" stroke-width="3"/>',
            f'<text x="{x:.1f}" y="{PLOT_BOTTOM+62}" text-anchor="middle" font-family="Arial" font-size="31" fill="{INK}">{value:.1f}</text>',
        ]
    elements += [
        f'<line x1="{LEFT}" y1="{TOP}" x2="{LEFT}" y2="{PLOT_BOTTOM}" stroke="{INK}" stroke-width="4"/>',
        f'<line x1="{LEFT}" y1="{PLOT_BOTTOM}" x2="{PLOT_RIGHT}" y2="{PLOT_BOTTOM}" stroke="{INK}" stroke-width="4"/>',
        f'<text x="{WIDTH/2}" y="{HEIGHT-70}" text-anchor="middle" font-family="Arial" font-size="39" fill="{INK}">Model parameters (millions)</text>',
        f'<text x="76" y="{(TOP+PLOT_BOTTOM)/2}" text-anchor="middle" transform="rotate(-90 76 {(TOP+PLOT_BOTTOM)/2})" font-family="Arial" font-size="39" fill="{INK}">Mean five-fold macro F1</text>',
    ]
    label_offsets = {
        "MobileViT-XS": (32, -45, "start"),
        "MobileNetV2": (-28, -42, "end"),
        "MobileNetV2-SE": (30, 55, "start"),
        "MobileNetV2-CBAM": (30, -38, "start"),
        "EfficientNet-B0": (-30, -40, "end"),
    }
    for name, parameters, mean_f1, std_f1 in MODELS:
        x, y = x_position(parameters), y_position(mean_f1)
        y_top, y_bottom = y_position(mean_f1 + std_f1), y_position(mean_f1 - std_f1)
        elements += [
            f'<line x1="{x:.1f}" y1="{y_top:.1f}" x2="{x:.1f}" y2="{y_bottom:.1f}" stroke="{MID}" stroke-width="4"/>',
            f'<line x1="{x-14:.1f}" y1="{y_top:.1f}" x2="{x+14:.1f}" y2="{y_top:.1f}" stroke="{MID}" stroke-width="4"/>',
            f'<line x1="{x-14:.1f}" y1="{y_bottom:.1f}" x2="{x+14:.1f}" y2="{y_bottom:.1f}" stroke="{MID}" stroke-width="4"/>',
        ]
        selected = name == "MobileViT-XS"
        if selected:
            points = " ".join(f"{px:.1f},{py:.1f}" for px, py in star_points(x, y, 26, 12))
            elements.append(f'<polygon points="{points}" fill="{ORANGE}" stroke="{ORANGE_EDGE}" stroke-width="3"/>')
        else:
            elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="14" fill="{BLUE}" stroke="{BLUE_EDGE}" stroke-width="3"/>')
        dx, dy, anchor = label_offsets[name]
        label = "MobileViT-XS (selected)" if selected else name
        weight = "700" if selected else "400"
        elements.append(f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" text-anchor="{anchor}" font-family="Arial" font-size="31" font-weight="{weight}" fill="{INK}">{escape(label)}</text>')
    elements += [
        f'<text x="{LEFT+15}" y="{PLOT_BOTTOM-22}" font-family="Arial" font-size="27" fill="{MID}">Error bars show sample standard deviation across five folds.</text>',
        '</svg>',
    ]
    output.with_suffix(".svg").write_text("\n".join(elements), encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    output_dir = root / "outputs" / "thesis_figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "classifier_accuracy_efficiency"
    make_png_and_pdf(output)
    make_svg(output)
    for suffix in (".png", ".svg", ".pdf"):
        print(f"Saved {output.with_suffix(suffix)}")


if __name__ == "__main__":
    main()
