"""Build the Wyoming wind capacity-factor datasets from PUDL.

Usage:
    python scripts/build_wind_capacity_factors.py [--cache DIR] [--eia923 PATH_TO_EIA923_Schedules_2_3_4_5_M_12_2025_Final.xlsx]

A capacity factor is the electricity a plant generated in a period divided by what it would have generated running
at its nameplate capacity for the whole period. This script computes it for every wind plant in Wyoming, for each
year from 2001 to 2025 and each month of those years, and writes three files to ``data/``:

    wyoming_wind_plant_years.csv     one row per plant and year
    wyoming_wind_plant_months.csv    one row per plant and month, for plant-years that count (see below)
    wyoming_wind_fleet.csv           the fleet capacity factor for each year, and for each calendar month

A plant-year counts only if every wind generator at the plant was operating for the whole year at the same
nameplate capacity: no generator entered service or retired during the year, and the plant's wind capacity is the
same as in the year before. Other plant-years are kept in the plant-year file, with the reason they do not count,
but have no capacity factor. Without this rule a plant's first year, or a year in which turbines were added or
retired, would show a capacity factor that is too low or too high.

Generation is EIA-923 net generation from wind (fuel code WND), by plant. Capacity is EIA-860 nameplate capacity of
the plant's existing wind generators. If ``--eia923`` is given, every plant's annual and monthly net generation for
the final year is cross-checked against EIA's own EIA-923 workbook.
"""
import argparse
import calendar
import json
import pathlib
import urllib.request

import pandas as pd

YEAR = 2025
FIRST_YEAR = 2001
STATE = "WY"
PUDL = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/stable/{}.parquet"
TABLES = [
    "out_eia__yearly_generators",
    "out_eia923__yearly_generation_fuel_combined",
    "out_eia923__monthly_generation_fuel_combined",
]
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data"


def fetch(table, cache):
    path = cache / f"{table}.parquet"
    if not path.exists():
        urllib.request.urlretrieve(PUDL.format(table), path)
    return path


def hours_in_year(y):
    return 8784 if calendar.isleap(y) else 8760


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(ROOT / ".cache"))
    ap.add_argument("--eia923", default=None)
    args = ap.parse_args()
    cache = pathlib.Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)

    # ---- Wind generators in Wyoming, by year ----
    gcols = ["plant_id_eia", "plant_name_eia", "generator_id", "report_date", "state", "county", "latitude",
             "longitude", "utility_name_eia", "fuel_type_code_pudl", "operational_status", "capacity_mw",
             "generator_operating_date", "generator_retirement_date", "net_generation_mwh"]
    gens = pd.read_parquet(fetch(TABLES[0], cache), columns=gcols)
    gens["year"] = pd.to_datetime(gens["report_date"]).dt.year
    wind = gens[(gens["state"] == STATE) & (gens["fuel_type_code_pudl"] == "wind")
                & (gens["operational_status"] == "existing")
                & gens["year"].between(FIRST_YEAR, YEAR)].copy()
    wind["op_year"] = pd.to_datetime(wind["generator_operating_date"]).dt.year
    # A generator's retirement date often appears only in the editions after it retires; in the year it retires it
    # is still reported as existing, with no date. Take the date from whichever edition reports it.
    all_wind = gens[(gens["state"] == STATE) & (gens["fuel_type_code_pudl"] == "wind")]
    ret_date = (all_wind.dropna(subset=["generator_retirement_date"])
                .groupby(["plant_id_eia", "generator_id"])["generator_retirement_date"].max())
    wind["ret_year"] = pd.to_datetime(
        pd.Series([ret_date.get(k) for k in zip(wind["plant_id_eia"], wind["generator_id"])],
                  index=wind.index)).dt.year
    plant_ids = sorted(wind["plant_id_eia"].unique())

    py = (wind.groupby(["plant_id_eia", "year"])
          .agg(capacity_mw=("capacity_mw", "sum"), generators=("generator_id", "size"),
               last_entry_year=("op_year", "max"), first_retirement_year=("ret_year", "min"),
               pudl_generator_mwh=("net_generation_mwh", "sum"))
          .reset_index())
    latest = (gens[gens["plant_id_eia"].isin(plant_ids)].sort_values("report_date")
              .groupby("plant_id_eia").last()[["plant_name_eia", "county", "latitude", "longitude",
                                               "utility_name_eia"]])
    first_op = wind.groupby("plant_id_eia")["generator_operating_date"].min()

    # ---- Net generation from wind, by plant and year, and by plant and month ----
    gfcols = ["report_date", "plant_id_eia", "fuel_type_code_pudl", "net_generation_mwh", "data_maturity"]
    filt = [("plant_id_eia", "in", [int(p) for p in plant_ids])]
    gy = pd.read_parquet(fetch(TABLES[1], cache), columns=gfcols, filters=filt)
    gm = pd.read_parquet(fetch(TABLES[2], cache), columns=gfcols, filters=filt)
    for d in (gy, gm):
        d["year"] = pd.to_datetime(d["report_date"]).dt.year
    gy = gy[(gy["fuel_type_code_pudl"] == "wind") & gy["year"].between(FIRST_YEAR, YEAR)]
    gm = gm[(gm["fuel_type_code_pudl"] == "wind") & gm["year"].between(FIRST_YEAR, YEAR)]
    maturity = sorted(gy.loc[gy["year"] == YEAR, "data_maturity"].dropna().unique().tolist())
    gy = gy.groupby(["plant_id_eia", "year"])["net_generation_mwh"].sum().rename("net_generation_mwh")
    gm["month"] = pd.to_datetime(gm["report_date"]).dt.month
    gm = gm.groupby(["plant_id_eia", "year", "month"])["net_generation_mwh"].sum().rename("net_generation_mwh")

    py = py.merge(gy.reset_index(), on=["plant_id_eia", "year"], how="left")
    py["net_generation_mwh"] = py["net_generation_mwh"].fillna(0.0)
    py = py.sort_values(["plant_id_eia", "year"])
    py["prev_capacity_mw"] = py.groupby("plant_id_eia")["capacity_mw"].shift()
    py["prev_year"] = py.groupby("plant_id_eia")["year"].shift()

    def reason(r):
        if r["last_entry_year"] >= r["year"]:
            return "generator entered service during year"
        if pd.notna(r["first_retirement_year"]) and r["first_retirement_year"] <= r["year"]:
            return "generator retired during year"
        if pd.isna(r["prev_year"]) or r["prev_year"] != r["year"] - 1:
            return "no capacity record for the previous year"
        if abs(r["capacity_mw"] - r["prev_capacity_mw"]) > 0.05:
            return "capacity changed during year"
        if r["net_generation_mwh"] <= 0:
            return "no net generation reported"
        return ""

    py["excluded_reason"] = py.apply(reason, axis=1)
    py["counted"] = py["excluded_reason"] == ""
    py["hours"] = py["year"].map(hours_in_year)
    py["capacity_factor"] = (py["net_generation_mwh"] / (py["capacity_mw"] * py["hours"])).where(py["counted"])
    py = py.join(latest, on="plant_id_eia")
    py["first_operating_date"] = py["plant_id_eia"].map(first_op)

    # ---- Monthly, for counted plant-years ----
    pm = gm.reset_index().merge(py.loc[py["counted"], ["plant_id_eia", "year", "capacity_mw", "plant_name_eia"]],
                                on=["plant_id_eia", "year"], how="inner")
    pm["hours"] = [calendar.monthrange(y, m)[1] * 24 for y, m in zip(pm["year"], pm["month"])]
    pm["capacity_factor"] = pm["net_generation_mwh"] / (pm["capacity_mw"] * pm["hours"])

    # ---- Fleet capacity factors: generation-weighted over counted plants ----
    c = py[py["counted"]].assign(possible=lambda d: d["capacity_mw"] * d["hours"])
    fleet_y = c.groupby("year").agg(plants=("plant_id_eia", "size"), capacity_mw=("capacity_mw", "sum"),
                                    net_generation_mwh=("net_generation_mwh", "sum"),
                                    possible_mwh=("possible", "sum"),
                                    median_plant_cf=("capacity_factor", "median"))
    fleet_y["capacity_factor"] = fleet_y["net_generation_mwh"] / fleet_y["possible_mwh"]
    all_y = py.groupby("year").agg(all_plants=("plant_id_eia", "size"), all_capacity_mw=("capacity_mw", "sum"))
    # Total wind generation in Wyoming, including any reported by a plant whose wind generators had all retired.
    all_y["all_net_generation_mwh"] = gy.groupby(level="year").sum()
    fleet_y = all_y.join(fleet_y).reset_index()
    fleet_y["share_of_capacity_counted_pct"] = 100 * fleet_y["capacity_mw"] / fleet_y["all_capacity_mw"]

    recent = pm[pm["year"].between(YEAR - 9, YEAR)].assign(possible=lambda d: d["capacity_mw"] * d["hours"])
    fleet_m = recent.groupby("month").agg(net_generation_mwh=("net_generation_mwh", "sum"),
                                          possible_mwh=("possible", "sum"))
    fleet_m["capacity_factor"] = fleet_m["net_generation_mwh"] / fleet_m["possible_mwh"]
    fleet_m = fleet_m.reset_index()

    # ---- Checks ----
    checks = {"year": YEAR, "first_year": FIRST_YEAR, "data_maturity_final_year": maturity}
    # 1. Monthly and annual EIA-923 tables agree for every plant-year.
    msum = gm.groupby(["plant_id_eia", "year"]).sum()
    both = py.set_index(["plant_id_eia", "year"])["net_generation_mwh"].to_frame("annual").join(
        msum.rename("monthly"), how="left").fillna(0.0)
    diff_m = (both["annual"] - both["monthly"]).abs()
    checks["max_abs_diff_monthly_vs_annual_mwh"] = round(float(diff_m.max()), 3)
    assert diff_m.max() < 1.0, "monthly and annual net generation disagree"
    # 2. PUDL's generator-level allocation agrees with plant-level generation for counted plant-years.
    cc = py[py["counted"] & py["pudl_generator_mwh"].notna() & (py["year"] >= 2008)]
    rel = ((cc["pudl_generator_mwh"] - cc["net_generation_mwh"]).abs() / cc["net_generation_mwh"])
    checks["counted_plant_years_compared_with_generator_allocation"] = int(len(cc))
    checks["max_rel_diff_generator_allocation"] = round(float(rel.max()), 6)
    assert rel.max() < 0.005, "PUDL generator allocation disagrees with plant generation"
    # 3. Optional: EIA's own EIA-923 workbook for the final year.
    if args.eia923:
        x = pd.read_excel(args.eia923, "Page 1 Generation and Fuel Data", skiprows=5)
        x = x[(x["Plant State"] == STATE) & (x["Reported\nFuel Type Code"] == "WND")]
        months = [f"Netgen\n{calendar.month_name[m]}" for m in range(1, 13)]
        # EIA marks months not yet reported (and some empty cells) with "." rather than a number.
        for col in months + ["Net Generation\n(Megawatthours)"]:
            x[col] = pd.to_numeric(x[col], errors="coerce").fillna(0.0)
        x = x.groupby("Plant Id")[months + ["Net Generation\n(Megawatthours)"]].sum()
        mine_y = py[py["year"] == YEAR].set_index("plant_id_eia")["net_generation_mwh"]
        mine_y = mine_y[mine_y != 0]
        eia_y = x["Net Generation\n(Megawatthours)"]
        eia_y = eia_y[eia_y != 0]
        assert set(mine_y.index) == set(eia_y.index), "plants with wind generation differ from EIA-923"
        d_y = (mine_y - eia_y.reindex(mine_y.index)).abs()
        mine_m = gm.xs(YEAR, level="year").unstack("month").reindex(columns=range(1, 13)).fillna(0.0)
        eia_m = x[months].set_axis(range(1, 13), axis=1).reindex(mine_m.index).fillna(0.0)
        d_m = (mine_m - eia_m).abs()
        checks["eia923_plants_compared"] = int(len(mine_y))
        checks["eia923_total_wind_mwh"] = round(float(eia_y.sum()), 0)
        checks["pudl_total_wind_mwh"] = round(float(mine_y.sum()), 0)
        checks["eia923_max_abs_diff_annual_mwh"] = round(float(d_y.max()), 3)
        checks["eia923_max_abs_diff_monthly_mwh"] = round(float(d_m.values.max()), 3)
        assert d_y.max() < 1.0 and d_m.values.max() < 1.0, "PUDL wind generation disagrees with EIA-923"

    cy = py[(py["year"] == YEAR) & py["counted"]]
    checks.update({
        "plants_final_year": int((py["year"] == YEAR).sum()),
        "counted_plants_final_year": int(len(cy)),
        "fleet_capacity_factor_final_year": round(float(fleet_y.set_index("year").loc[YEAR, "capacity_factor"]), 4),
        "counted_plant_years": int(py["counted"].sum()),
        "excluded_plant_years": {k: int(v) for k, v in
                                 py.loc[~py["counted"], "excluded_reason"].value_counts().items()},
    })

    # ---- Write ----
    pcols = ["plant_id_eia", "plant_name_eia", "year", "county", "latitude", "longitude", "utility_name_eia",
             "first_operating_date", "generators", "capacity_mw", "net_generation_mwh", "hours", "counted",
             "excluded_reason", "capacity_factor"]
    out_py = py[pcols].sort_values(["plant_name_eia", "year"])
    out_py["capacity_mw"] = out_py["capacity_mw"].round(1)
    out_py["net_generation_mwh"] = out_py["net_generation_mwh"].round(0)
    out_py["capacity_factor"] = out_py["capacity_factor"].round(4)
    out_py.to_csv(OUT / "wyoming_wind_plant_years.csv", index=False, date_format="%Y-%m-%d")
    out_pm = pm[["plant_id_eia", "plant_name_eia", "year", "month", "capacity_mw", "net_generation_mwh", "hours",
                 "capacity_factor"]].sort_values(["plant_name_eia", "year", "month"])
    out_pm["capacity_factor"] = out_pm["capacity_factor"].round(4)
    out_pm.to_csv(OUT / "wyoming_wind_plant_months.csv", index=False)
    fy = fleet_y.round({"all_capacity_mw": 1, "capacity_mw": 1, "net_generation_mwh": 0, "possible_mwh": 0,
                        "all_net_generation_mwh": 0, "capacity_factor": 6, "median_plant_cf": 4,
                        "share_of_capacity_counted_pct": 1})
    fy.insert(0, "period", "year")
    fm = fleet_m.round({"net_generation_mwh": 0, "possible_mwh": 0, "capacity_factor": 6})
    fm.insert(0, "period", f"month, {YEAR - 9}-{YEAR}")
    pd.concat([fy, fm], ignore_index=True).to_csv(OUT / "wyoming_wind_fleet.csv", index=False)
    (OUT / "wind_checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
