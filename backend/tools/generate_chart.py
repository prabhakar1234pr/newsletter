"""Step 3b: Data chart generation via Matplotlib.

Reads chart_data from newsletter content and produces a branded PNG chart
with pixel-perfect numerical accuracy.

Usage:
    uv run python tools/generate_chart.py --input .tmp/newsletter_content.json
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = PROJECT_ROOT / ".tmp" / "newsletter_content.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".tmp"

# Brand palette
PRIMARY_BLUE = "#2F94FB"
DEEP_BLUE = "#2367D3"
INDIGO = "#4B3FE0"
PURPLE = "#8331A6"
BRAND_COLORS = [PRIMARY_BLUE, DEEP_BLUE, INDIGO, PURPLE, "#5BA8FC", "#6B52E8"]

# Try to use Poppins if installed, fall back to Arial
FONT_FAMILY = "Poppins"
try:
    fm.findfont(FONT_FAMILY, fallback_to_default=False)
except ValueError:
    FONT_FAMILY = "Arial"


def apply_brand_style():
    """Set matplotlib rcParams for branded charts."""
    plt.rcParams.update({
        "font.family": FONT_FAMILY,
        "font.size": 12,
        "axes.titlesize": 16,
        "axes.titleweight": "bold",
        "axes.labelsize": 13,
        "axes.edgecolor": "#CCCCCC",
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linewidth": 0.5,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "xtick.labelsize": 11,
        "ytick.labelsize": 11,
    })


def generate_bar_chart(chart_data: dict, output_path: Path):
    """Generate a branded bar chart."""
    fig, ax = plt.subplots(figsize=(8, 5))

    labels = chart_data["labels"]
    values = chart_data["values"]
    colors = BRAND_COLORS[:len(labels)]

    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=0.5)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                str(val), ha="center", va="bottom", fontweight="bold", fontsize=11)

    ax.set_title(chart_data.get("title", ""), pad=15)
    ax.set_xlabel(chart_data.get("x_label", ""))
    ax.set_ylabel(chart_data.get("y_label", ""))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def generate_line_chart(chart_data: dict, output_path: Path):
    """Generate a branded line chart."""
    fig, ax = plt.subplots(figsize=(8, 5))

    labels = chart_data["labels"]
    values = chart_data["values"]

    ax.plot(labels, values, color=PRIMARY_BLUE, linewidth=2.5, marker="o",
            markersize=8, markerfacecolor=DEEP_BLUE, markeredgecolor="white", markeredgewidth=2)

    # Fill under the line
    ax.fill_between(range(len(labels)), values, alpha=0.1, color=PRIMARY_BLUE)

    ax.set_title(chart_data.get("title", ""), pad=15)
    ax.set_xlabel(chart_data.get("x_label", ""))
    ax.set_ylabel(chart_data.get("y_label", ""))
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def generate_pie_chart(chart_data: dict, output_path: Path):
    """Generate a branded pie chart."""
    fig, ax = plt.subplots(figsize=(7, 7))

    labels = chart_data["labels"]
    values = chart_data["values"]
    colors = BRAND_COLORS[:len(labels)]

    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=colors, autopct="%1.1f%%",
        startangle=90, pctdistance=0.75,
        wedgeprops={"edgecolor": "white", "linewidth": 2},
    )
    for text in autotexts:
        text.set_fontweight("bold")
        text.set_color("white")

    ax.set_title(chart_data.get("title", ""), pad=20, fontweight="bold")

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


CHART_GENERATORS = {
    "bar": generate_bar_chart,
    "line": generate_line_chart,
    "pie": generate_pie_chart,
}


def main():
    parser = argparse.ArgumentParser(description="Generate branded data chart via Matplotlib")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Content JSON path")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    content = json.loads(args.input.read_text(encoding="utf-8"))
    chart_data = content.get("chart_data")

    if not chart_data:
        print("No chart_data in content, skipping chart generation.", file=sys.stderr)
        sys.exit(0)

    chart_type = chart_data.get("type", "bar").lower()
    if chart_type not in CHART_GENERATORS:
        print(f"WARNING: Unknown chart type '{chart_type}', defaulting to bar", file=sys.stderr)
        chart_type = "bar"

    apply_brand_style()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "chart_001.png"

    print(f"Generating {chart_type} chart...", file=sys.stderr)
    CHART_GENERATORS[chart_type](chart_data, output_path)

    if output_path.exists() and output_path.stat().st_size > 0:
        print(f"Chart saved to {output_path}", file=sys.stderr)
        print(str(output_path))
    else:
        print("ERROR: Chart file was not created", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
