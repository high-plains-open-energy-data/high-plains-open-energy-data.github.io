"""Build the Wyoming transmission map from OpenStreetMap data.

Usage:
    python scripts/build_transmission_map.py --lines wy_lines.geojson --substations wy_substations.geojson \
        --counties cb_2023_us_county_500k.zip --osm-date "20 October 2026"

The inputs are Wyoming's power lines and substations extracted from OpenStreetMap through the Overpass API, and
the U.S. Census Bureau's cartographic county boundaries. The outputs are a static map, two GeoJSON files and a
summary of line length by voltage. Map data (c) OpenStreetMap contributors, available under the Open Database
Licence (ODbL); the GeoJSON files derived from it are released under the ODbL.
"""
import argparse
import json
import pathlib

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
CLASSES = [(500, "500 kV", "#7b2cbf", 3.0), (345, "345 kV", "#d62828", 2.4), (230, "230 kV", "#f77f00", 1.8),
           (161, "161 kV", "#e9c46a", 1.5), (138, "138 kV", "#2a9d8f", 1.4), (115, "115 kV", "#1d70b8", 1.2),
           (69, "69 kV", "#6c757d", 0.8)]
TOWNS = {"Cheyenne": (-104.82, 41.14), "Casper": (-106.31, 42.85), "Laramie": (-105.59, 41.31),
         "Gillette": (-105.50, 44.29), "Rock Springs": (-109.20, 41.59), "Sheridan": (-106.96, 44.80),
         "Evanston": (-110.96, 41.27), "Riverton": (-108.38, 43.02), "Jackson": (-110.76, 43.48),
         "Cody": (-109.06, 44.53), "Rawlins": (-107.24, 41.79), "Newcastle": (-104.20, 43.85),
         "Douglas": (-105.38, 42.76), "Worland": (-107.96, 44.02), "Kemmerer": (-110.54, 41.79)}


def voltage_class(kv):
    if kv is None or kv != kv:
        return None
    for c, *_ in CLASSES:
        if kv >= c - 5:
            return c
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", required=True)
    ap.add_argument("--substations", required=True)
    ap.add_argument("--counties", required=True)
    ap.add_argument("--osm-date", required=True)
    args = ap.parse_args()

    counties = gpd.read_file(f"zip://{args.counties}")
    counties = counties[counties["STATEFP"] == "56"].to_crs(4326)
    state = counties.dissolve()
    lines = gpd.read_file(args.lines)
    subs = gpd.read_file(args.substations)
    lines["kv_class"] = lines["kv"].map(voltage_class)

    # Published copies, keeping only the OpenStreetMap-derived attributes.
    lines[["osm_id", "power", "name", "operator", "voltage_tag", "kv", "kv_class", "counties", "km_in_wy",
           "geometry"]].to_file(OUT / "wyoming_transmission_lines_osm.geojson", driver="GeoJSON")
    subs[["osm_id", "name", "operator", "voltage_tag", "kv", "county", "geometry"]].to_file(
        OUT / "wyoming_substations_osm.geojson", driver="GeoJSON")

    inside = gpd.clip(lines, state)
    km = inside.to_crs(5070).length.groupby(inside["kv_class"].fillna(0)).sum() / 1000
    summary = {"osm_date": args.osm_date, "lines": int(len(lines)), "substations": int(len(subs)),
               "km_by_voltage_class": {("untagged" if k == 0 else f"{int(k)} kV"): round(float(v))
                                       for k, v in km.sort_index(ascending=False).items()},
               "km_total": round(float(km.sum()))}
    (OUT / "wyoming_transmission_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    fig, ax = plt.subplots(figsize=(13, 8.5), dpi=150)
    counties.boundary.plot(ax=ax, color="#c9c9c9", linewidth=0.5)
    state.boundary.plot(ax=ax, color="#555555", linewidth=1.0)
    untagged = inside[inside["kv_class"].isna()]
    untagged.plot(ax=ax, color="#9e9e9e", linewidth=0.5, linestyle=(0, (2, 2)))
    for c, label, colour, width in reversed(CLASSES):
        part = inside[inside["kv_class"] == c]
        if len(part):
            part.plot(ax=ax, color=colour, linewidth=width)
    subs.plot(ax=ax, color="#222222", markersize=3, zorder=5)
    for name, (x, y) in TOWNS.items():
        ax.plot(x, y, "s", color="white", markeredgecolor="#222222", markersize=3.5, zorder=6)
        ax.annotate(name, (x, y), xytext=(4, 3), textcoords="offset points", fontsize=7, zorder=7)
    handles = [Line2D([0], [0], color=col, lw=w + 0.6, label=f"{lab} ({km.get(c, 0):,.0f} km)")
               for c, lab, col, w in CLASSES if km.get(c, 0) > 0]
    handles.append(Line2D([0], [0], color="#9e9e9e", lw=1, ls=(0, (2, 2)),
                          label=f"Voltage not tagged ({km.get(0, 0):,.0f} km)"))
    handles.append(Line2D([0], [0], marker="o", color="none", markerfacecolor="#222222", markersize=4,
                          label=f"Substation ({len(subs)})"))
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=8, frameon=False,
              title="Lines in Wyoming", title_fontsize=9, alignment="left")
    ax.set_title("Wyoming's electric transmission network, 69 kV and above", fontsize=13, loc="left")
    ax.text(0, -0.04, f"Map data © OpenStreetMap contributors (ODbL), as of {args.osm_date}. "
            "County boundaries: U.S. Census Bureau. High Plains Open Energy Data.",
            transform=ax.transAxes, fontsize=7, color="#555555")
    ax.set_axis_off()
    ax.set_aspect(1 / 0.743)  # approximate scale correction at 42 degrees north
    (ROOT / "assets").mkdir(exist_ok=True)
    fig.savefig(ROOT / "assets" / "wyoming_transmission_map.png", bbox_inches="tight")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
