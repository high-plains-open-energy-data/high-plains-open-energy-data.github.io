"""Build the Wyoming interconnection-queue dataset from Berkeley Lab's Queued Up data file.

Usage:
    python scripts/build_wyoming_queue.py --lbnl PATH_TO_LBNL_Ix_Queue_Data_File_thru2025.xlsx

Berkeley Lab publishes the Queued Up data file once a year at https://emp.lbl.gov/queues under CC-BY-4.0
(attribution: Lawrence Berkeley National Laboratory and GridTracker). This script selects the interconnection
requests located in Wyoming, writes them to ``data/``, and checks the active capacity it computes against the
state totals that Berkeley Lab publishes in the same file (sheet "11. Active Cap. Maps").
"""
import argparse
import json
import pathlib

import openpyxl
import pandas as pd

STATE = "WY"
EDITION = "Queued Up 2026 Edition (requests through the end of 2025)"
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
COLUMNS = [
    "entity", "q_id", "project_name", "developer", "utility", "county", "poi_name", "service", "type_clean",
    "type_1", "type_2", "type_3", "mw_1", "q_status", "IA_phase_clean", "q_date", "ia_date", "prop_date",
    "wd_date", "on_date",
]
# Berkeley Lab's own state totals use these categories for the type of the first resource.
CHECKED_TYPES = ["Gas", "Solar", "Wind"]


def published_state_totals(path):
    """Cumulative active capacity (GW) by type for Wyoming, as published by Berkeley Lab."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["11. Active Cap. Maps"]
    rows = [[v for v in r if v is not None] for r in ws.iter_rows(values_only=True)]
    # The state table lists rows of [state, type, GW]; the cumulative table is the one with the larger totals.
    tables = {}
    for r in rows:
        for i in range(len(r) - 2):
            if r[i] == STATE and isinstance(r[i + 2], (int, float)):
                tables.setdefault(r[i + 1], []).append(float(r[i + 2]))
    return {t: max(v) for t, v in tables.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lbnl", required=True)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)

    df = pd.read_excel(args.lbnl, sheet_name="03. Complete Queue Data", header=1)
    wy = df[df["state"] == STATE][COLUMNS].copy()
    # A few queue IDs were stored by Excel as dates; keep every ID as text, as it appears in the file.
    wy["q_id"] = wy["q_id"].map(lambda v: v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v))
    wy = wy.sort_values(["q_status", "q_date", "entity", "q_id"])
    wy.to_csv(OUT / "wyoming_interconnection_queue.csv", index=False, date_format="%Y-%m-%d")

    active = wy[wy["q_status"] == "active"]
    withdrawn = wy[wy["q_status"] == "withdrawn"]
    dated = withdrawn[withdrawn["wd_date"].notna()]
    years_to_wd = (dated["wd_date"] - dated["q_date"]).dt.days / 365.25
    early = wy[wy["q_date"].dt.year <= 2020]

    by_status = wy.groupby("q_status")["mw_1"].agg(["count", "sum"])
    by_type = active.groupby("type_1")["mw_1"].agg(["count", "sum"]).sort_values("sum", ascending=False)
    by_phase = active.groupby("IA_phase_clean")["mw_1"].agg(["count", "sum"]).sort_values("sum", ascending=False)
    by_entity = active.groupby("entity")["mw_1"].agg(["count", "sum"]).sort_values("sum", ascending=False)
    coverage = withdrawn.groupby("entity")["wd_date"].agg(dated="count", total="size").sort_values(
        "total", ascending=False)
    by_year = wy.groupby([wy["q_date"].dt.year, "q_status"]).size().unstack(fill_value=0)

    def frame(d):
        return {str(k): {c: (int(v) if c in ("count", "dated", "total") else round(float(v), 1))
                         for c, v in row.items()}
                for k, row in d.iterrows()}

    published = published_state_totals(args.lbnl)
    computed = {t: round(float(active.loc[active["type_1"] == t, "mw_1"].sum()) / 1000, 4) for t in CHECKED_TYPES}
    for t in CHECKED_TYPES:
        assert abs(computed[t] - published[t]) < 0.0005, (t, computed[t], published[t])

    summary = {
        "edition": EDITION,
        "requests": int(len(wy)),
        "by_status": frame(by_status),
        "active_by_type": frame(by_type),
        "active_by_phase": frame(by_phase),
        "active_by_entity": frame(by_entity),
        "withdrawal_date_coverage": frame(coverage),
        "withdrawn_with_date": int(len(dated)),
        "median_years_request_to_withdrawal_dated": round(float(years_to_wd.median()), 1),
        "requests_entered_2020_or_earlier": frame(early.groupby("q_status").size().to_frame("count")),
        "requests_by_year_and_status": {str(y): {k: int(v) for k, v in r.items()} for y, r in by_year.iterrows()},
        "checks": {
            "active_gw_computed": computed,
            "active_gw_published_by_lbnl": {t: published[t] for t in CHECKED_TYPES},
            "match": True,
        },
    }
    (OUT / "wyoming_queue_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary["checks"], indent=2))
    print(f"{len(wy)} Wyoming requests written")


if __name__ == "__main__":
    main()
