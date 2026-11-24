"""System architecture diagram for the application: figures/architecture.png.

Blue boxes are built and working (model, control logic, app); grey dashed boxes are concept hardware.
Run: .venv/bin/python src/diagram.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "figures" / "architecture.png"

SURFACE, INK, INK2 = "#fcfcfb", "#14213d", "#52514e"
BUILT_FILL, BUILT_EDGE = "#e4eefb", "#1e6fd9"  # brand blue
CONCEPT_FILL, CONCEPT_EDGE = "#f1f0ec", "#8a8984"


def box(ax, x, y, w, h, title, lines, built):
    style = dict(boxstyle="round,pad=0.02,rounding_size=0.12", linewidth=1.6,
                 facecolor=BUILT_FILL if built else CONCEPT_FILL,
                 edgecolor=BUILT_EDGE if built else CONCEPT_EDGE,
                 linestyle="-" if built else (0, (4, 3)))
    ax.add_patch(FancyBboxPatch((x, y), w, h, **style))
    ax.text(x + w / 2, y + h - 0.32, title, ha="center", va="top", fontsize=11, fontweight="bold", color=INK)
    ax.text(x + w / 2, y + h - 0.78, "\n".join(lines), ha="center", va="top", fontsize=8.6,
            color=INK2, linespacing=1.45)


def arrow(ax, start, end):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=14, linewidth=1.5, color=INK2))


def label(ax, x, y, text, ha="center", size=8.2):
    ax.text(x, y, text, ha=ha, va="center", fontsize=size, color=INK2, style="italic")


def main() -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans"})
    fig, ax = plt.subplots(figsize=(13, 5.4))
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    ax.set_xlim(0, 25.5)
    ax.set_ylim(0.3, 11.2)
    ax.axis("off")

    top_y, bottom_y, h = 6.2, 0.8, 3.0
    # Main flow, left to right
    box(ax, 0.3, top_y, 4.8, h, "1. Room sensors",
        ["Temperature + humidity", "Window open / closed", "ESP32 board, battery", "Every 15 minutes"], built=False)
    box(ax, 6.3, top_y, 4.9, h, "2. Building gateway",
        ["Collects all rooms", "Wi-Fi / Zigbee", "Small local computer", "Works without internet"], built=False)
    box(ax, 12.4, top_y, 5.6, h, "3. Forecast model",
        ["Machine learning (LightGBM)", "Room temperature 1-3 h ahead", "Error 0.08 °C (1 h), 0.17 °C (3 h)",
         "measured on real data"], built=True)
    box(ax, 19.2, top_y, 6.0, h, "4. Decision",
        ["Forecast above 22 °C?", "-> turn the radiator down now", "Forecast above 23.5 °C?",
         "-> send an overheating alert"], built=True)

    # Inputs and outputs
    box(ax, 12.4, 9.75, 5.6, 1.3, "Weather forecast", ["Open-Meteo, free, hourly"], built=True)
    box(ax, 19.2, bottom_y, 6.0, h, "5a. Smart radiator valve",
        ["One per radiator, battery", "Opens 0-100 %", "Room gets less heat", "and stays at 21-22 °C"], built=False)
    box(ax, 12.4, bottom_y, 5.6, h, "5b. iPhone app",
        ["Room now + 3-hour forecast", "Overheating alerts", "Tips: keep the window closed",
         "kWh and CO2 saved"], built=True)
    box(ax, 6.3, bottom_y, 4.9, h, "5c. Building report",
        ["For the building manager", "Overheated rooms", "Heat saved per month"], built=False)

    mid = top_y + h / 2
    arrow(ax, (5.1, mid), (6.3, mid))
    label(ax, 5.7, mid + 0.4, "data", size=7.6)
    arrow(ax, (11.2, mid), (12.4, mid))
    label(ax, 11.8, mid + 0.4, "data", size=7.6)
    arrow(ax, (18.0, mid), (19.2, mid))
    arrow(ax, (15.2, 9.75), (15.2, top_y + h))

    arrow(ax, (22.2, top_y), (22.2, bottom_y + h))
    label(ax, 22.4, (top_y + bottom_y + h) / 2, "valve setting", ha="left")
    arrow(ax, (19.8, top_y), (17.4, bottom_y + h))
    label(ax, 19.15, (top_y + bottom_y + h) / 2 - 0.1, "alerts\nand advice", ha="left")
    arrow(ax, (13.0, top_y), (10.6, bottom_y + h))
    label(ax, 11.45, (top_y + bottom_y + h) / 2 - 0.1, "monthly\nsummary", ha="right")

    # Legend, bottom left
    ax.add_patch(FancyBboxPatch((0.5, 2.85), 0.55, 0.45, boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor=BUILT_FILL, edgecolor=BUILT_EDGE, linewidth=1.4))
    ax.text(1.25, 3.07, "Built and working", va="center", fontsize=9.5, color=INK)
    ax.text(1.25, 2.62, "(our prototype)", va="center", fontsize=8.5, color=INK2)
    ax.add_patch(FancyBboxPatch((0.5, 1.55), 0.55, 0.45, boxstyle="round,pad=0.02,rounding_size=0.08",
                                facecolor=CONCEPT_FILL, edgecolor=CONCEPT_EDGE, linewidth=1.4,
                                linestyle=(0, (4, 3))))
    ax.text(1.25, 1.77, "Concept hardware", va="center", fontsize=9.5, color=INK)
    ax.text(1.25, 1.32, "(not built yet)", va="center", fontsize=8.5, color=INK2)

    ax.text(0.3, 10.4, "SmartHeat: how it works", fontsize=15, fontweight="bold", color=INK, va="center")
    logo = plt.imread(ROOT / "docs" / "brand" / "logo.png")
    ax.imshow(logo, extent=(19.6, 25.2, 9.85, 11.0), aspect="auto", zorder=5)
    ax.set_xlim(0, 25.5)
    ax.set_ylim(0.3, 11.2)
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor=SURFACE)
    print(f"-> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
