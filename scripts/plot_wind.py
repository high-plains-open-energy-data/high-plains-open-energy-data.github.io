"""Draw the two wind charts for the website from data/wyoming_wind_fleet.csv.

Usage:
    python scripts/plot_wind.py

Writes assets/wyoming_wind_fleet_cf.png and assets/wyoming_wind_monthly_cf.png. Requires matplotlib.
"""
import calendar
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
INK, MUTED, LINE, ACCENT = "#1d2327", "#5a646b", "#d5dadd", "#8a5a1f"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": LINE,
                     "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False})


def style(ax):
    ax.grid(axis="y", color=LINE, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))


def main():
    f = pd.read_csv(ROOT / "data" / "wyoming_wind_fleet.csv")
    yr = f[(f["period"] == "year") & f["capacity_factor"].notna()]
    mo = f[f["period"] != "year"]

    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=150)
    ax.plot(yr["year"], yr["capacity_factor"], color=ACCENT, linewidth=2, marker="o", markersize=4)
    style(ax)
    ax.set_ylim(0, 0.45)
    ax.set_xlim(yr["year"].min() - 0.5, yr["year"].max() + 0.5)
    ax.set_ylabel("Fleet capacity factor")
    last = yr.iloc[-1]
    ax.annotate(f"{last['capacity_factor']:.1%}", (last["year"], last["capacity_factor"]),
                xytext=(0, 8), textcoords="offset points", ha="center", color=INK, fontsize=9)
    fig.tight_layout()
    fig.savefig(ROOT / "assets" / "wyoming_wind_fleet_cf.png", facecolor="white")

    fig, ax = plt.subplots(figsize=(8, 3.6), dpi=150)
    ax.bar(mo["month"], mo["capacity_factor"], color=ACCENT, width=0.7)
    style(ax)
    ax.set_xticks(range(1, 13), [calendar.month_abbr[m] for m in range(1, 13)])
    ax.set_ylim(0, 0.55)
    ax.set_ylabel("Fleet capacity factor")
    fig.tight_layout()
    fig.savefig(ROOT / "assets" / "wyoming_wind_monthly_cf.png", facecolor="white")
    print("charts written")


if __name__ == "__main__":
    main()
