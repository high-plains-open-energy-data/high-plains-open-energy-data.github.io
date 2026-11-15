"""Build the history of planned retirement dates for Wyoming's coal units, one EIA-860 edition at a time.

Usage:
    python scripts/build_retirement_history.py [--cache DIR] [--verify YEAR=PATH ...]

Uses PUDL's ``out_eia__yearly_generators`` table, which keeps every annual EIA-860 edition. A unit is included
if it burned coal as its primary fuel in any edition, so units later converted to natural gas stay in the
history. Only final annual data is used; PUDL's monthly (EIA-860M) rows are excluded.

``--verify 2024=path/to/3_1_Generator_Y2024.xlsx`` compares the planned retirement month and year for every
included unit with EIA's own workbook for that year, and stops if any differ.
"""
import argparse
import json
import pathlib
import urllib.request

import pandas as pd

STATE = "WY"
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
PUDL = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/stable/{}.parquet"
TABLE = "out_eia__yearly_generators"
COLS = ["report_date", "state", "plant_id_eia", "plant_name_eia", "generator_id", "fuel_type_code_pudl",
        "energy_source_code_1", "capacity_mw", "operational_status", "operational_status_code",
        "planned_generator_retirement_date", "generator_retirement_date", "data_maturity"]


def fetch(cache):
    path = cache / f"{TABLE}.parquet"
    if not path.exists():
        urllib.request.urlretrieve(PUDL.format(TABLE), path)
    return path


def verify(history, year, path):
    """Compare planned retirement dates for one edition with EIA's workbook. Returns the number of units checked."""
    x = pd.ExcelFile(path)
    eia = []
    for sheet in ("Operable", "Retired and Canceled"):
        if sheet in x.sheet_names:
            d = pd.read_excel(x, sheet, skiprows=1)
            eia.append(d[d["State"] == STATE])
    eia = pd.concat(eia)
    eia["generator_id"] = eia["Generator ID"].astype(str)
    eia["plant_id_eia"] = eia["Plant Code"].astype(int)
    eia = eia.drop_duplicates(["plant_id_eia", "generator_id"]).set_index(["plant_id_eia", "generator_id"])
    ours = history[history["year"] == year].set_index(["plant_id_eia", "generator_id"])
    n = 0
    for key, row in ours.iterrows():
        if key not in eia.index or "Planned Retirement Year" not in eia.columns:
            continue
        e_year = pd.to_numeric(eia.loc[key, "Planned Retirement Year"], errors="coerce")
        e_month = pd.to_numeric(eia.loc[key, "Planned Retirement Month"], errors="coerce")
        d = row["planned_generator_retirement_date"]
        if pd.isna(e_year):
            assert pd.isna(d), (year, key, d)
        else:
            assert not pd.isna(d) and d.year == int(e_year) and d.month == int(e_month), (year, key, d, e_year)
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(ROOT / ".cache"))
    ap.add_argument("--verify", nargs="*", default=[], metavar="YEAR=PATH")
    args = ap.parse_args()
    cache = pathlib.Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)

    g = pd.read_parquet(fetch(cache), columns=COLS)
    g = g[(g["state"] == STATE) & (g["data_maturity"] == "final")].copy()
    g["year"] = pd.to_datetime(g["report_date"]).dt.year
    g["planned_generator_retirement_date"] = pd.to_datetime(g["planned_generator_retirement_date"])
    coal_units = g.loc[g["fuel_type_code_pudl"] == "coal", ["plant_id_eia", "generator_id"]].drop_duplicates()
    h = g.merge(coal_units, on=["plant_id_eia", "generator_id"])
    history = h[["year", "plant_id_eia", "plant_name_eia", "generator_id", "energy_source_code_1",
                 "fuel_type_code_pudl", "capacity_mw", "operational_status", "operational_status_code",
                 "planned_generator_retirement_date", "generator_retirement_date"]].sort_values(
        ["plant_name_eia", "generator_id", "year"])
    history.to_csv(OUT / "wyoming_coal_retirement_history.csv", index=False, date_format="%Y-%m-%d")

    # Units that have ever reported a planned retirement date, one row per unit and one column per edition.
    ever = history.groupby(["plant_id_eia", "generator_id"])["planned_generator_retirement_date"].transform(
        lambda s: s.notna().any())
    wide = history[ever].copy()
    wide["planned"] = wide["planned_generator_retirement_date"].dt.strftime("%Y-%m")
    wide = wide.pivot_table(index=["plant_name_eia", "generator_id", "plant_id_eia"], columns="year",
                            values="planned", aggfunc="first")
    wide.to_csv(OUT / "wyoming_coal_planned_retirement_by_edition.csv")

    checks = {"first_edition": int(history["year"].min()), "last_edition": int(history["year"].max()),
              "units": int(len(coal_units)), "units_with_a_planned_date_in_any_edition": int(len(wide)),
              "verified_against_eia": {}}
    for item in args.verify:
        year, path = item.split("=", 1)
        checks["verified_against_eia"][year] = verify(history, int(year), path)
    (OUT / "retirement_history_checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
