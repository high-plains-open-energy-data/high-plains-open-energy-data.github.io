"""Build the High Plains Open Energy Data Wyoming datasets from PUDL.

Usage:
    python scripts/build_wyoming_data.py [--cache DIR] [--eia860 PATH_TO_3_1_Generator_Y2025.xlsx]

Downloads three tables from the Public Utility Data Liberation project (PUDL),
maintained by Catalyst Cooperative and published under CC-BY-4.0, and writes the
Wyoming datasets to ``data/``. If ``--eia860`` is given, the generator counts and
capacities are cross-checked against the EIA-860 workbook itself.
"""
import argparse
import json
import pathlib
import urllib.request

import pandas as pd

YEAR = 2025
STATE = "WY"
PUDL = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/stable/{}.parquet"
TABLES = [
    "out_eia__yearly_generators",
    "out_eia923__yearly_generation_fuel_combined",
]
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data"

# EIA-860 proposed generator status codes (Form EIA-860 instructions, Table 6)
PROPOSED_STATUS = {
    "P": "Planned; regulatory approvals not initiated",
    "L": "Regulatory approvals pending; not under construction",
    "T": "Regulatory approvals received; not under construction",
    "U": "Under construction, 50 percent complete or less",
    "V": "Under construction, more than 50 percent complete",
    "TS": "Construction complete; not yet in commercial operation",
    "OT": "Other",
    "IP": "Indefinitely postponed, or no longer in resource plan",
    "CN": "Cancelled",
}
ACTIVE_PROPOSED = {"P", "L", "T", "U", "V", "TS", "OT"}


def fetch(table, cache):
    path = cache / f"{table}.parquet"
    if not path.exists():
        urllib.request.urlretrieve(PUDL.format(table), path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=str(ROOT / ".cache"))
    ap.add_argument("--eia860", default=None)
    args = ap.parse_args()
    cache = pathlib.Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)

    gens = pd.read_parquet(fetch(TABLES[0], cache))
    gens["year"] = pd.to_datetime(gens["report_date"]).dt.year
    wy = gens[(gens["state"] == STATE) & (gens["year"] == YEAR)].copy()

    # 1. Existing generators
    cols = [
        "plant_id_eia", "plant_name_eia", "generator_id", "utility_id_eia", "utility_name_eia",
        "county", "latitude", "longitude", "balancing_authority_code_eia", "fuel_type_code_pudl",
        "energy_source_code_1", "technology_description", "prime_mover_code", "operational_status_code",
        "capacity_mw", "summer_capacity_mw", "winter_capacity_mw", "generator_operating_date",
        "planned_generator_retirement_date",
    ]
    existing = wy[wy["operational_status"] == "existing"][cols].sort_values(["plant_name_eia", "generator_id"])
    existing.to_csv(OUT / "wyoming_generators_2025.csv", index=False, date_format="%Y-%m-%d")

    # 2. Capacity and generation by fuel (generation from plant-level EIA-923)
    gf = pd.read_parquet(fetch(TABLES[1], cache),
                         columns=["report_date", "plant_id_eia", "fuel_type_code_pudl", "net_generation_mwh"])
    gf["year"] = pd.to_datetime(gf["report_date"]).dt.year
    wy_ids = set(gens.loc[gens["state"] == STATE, "plant_id_eia"])
    gen = (gf[(gf["year"] == YEAR) & gf["plant_id_eia"].isin(wy_ids)]
           .groupby("fuel_type_code_pudl")["net_generation_mwh"].sum())
    cap = existing.groupby("fuel_type_code_pudl")["capacity_mw"].agg(["count", "sum"])
    summary = pd.DataFrame({
        "generators": cap["count"],
        "capacity_mw": cap["sum"].round(1),
        "net_generation_mwh": gen.round(0),
    }).fillna(0).sort_values("capacity_mw", ascending=False)
    summary["capacity_share_pct"] = (100 * summary["capacity_mw"] / summary["capacity_mw"].sum()).round(1)
    summary["generation_share_pct"] = (
        100 * summary["net_generation_mwh"] / summary["net_generation_mwh"].sum()).round(1)
    summary.index.name = "fuel_type_code_pudl"
    summary.to_csv(OUT / "wyoming_capacity_generation_by_fuel_2025.csv")

    # 3. Tracker: proposed generators and planned retirements
    pcols = [
        "plant_id_eia", "plant_name_eia", "generator_id", "utility_name_eia", "county",
        "technology_description", "fuel_type_code_pudl", "capacity_mw", "operational_status_code",
        "current_planned_generator_operating_date",
    ]
    proposed = wy[wy["operational_status"] == "proposed"][pcols].copy()
    proposed["status_description"] = proposed["operational_status_code"].map(PROPOSED_STATUS)
    proposed["active"] = proposed["operational_status_code"].isin(ACTIVE_PROPOSED)
    proposed = proposed.sort_values(["active", "current_planned_generator_operating_date", "plant_name_eia"],
                                    ascending=[False, True, True])
    proposed.to_csv(OUT / "wyoming_proposed_generators_2025.csv", index=False, date_format="%Y-%m-%d")

    retiring = existing[existing["planned_generator_retirement_date"].notna()][
        ["plant_id_eia", "plant_name_eia", "generator_id", "utility_name_eia", "technology_description",
         "fuel_type_code_pudl", "capacity_mw", "planned_generator_retirement_date"]]
    retiring.to_csv(OUT / "wyoming_planned_retirements_2025.csv", index=False, date_format="%Y-%m-%d")

    checks = {
        "existing_generators": int(len(existing)),
        "existing_capacity_mw": round(float(existing["capacity_mw"].sum()), 1),
        "active_proposed_generators": int(proposed["active"].sum()),
        "active_proposed_capacity_mw": round(float(proposed.loc[proposed["active"], "capacity_mw"].sum()), 1),
        "postponed_or_cancelled_generators": int((~proposed["active"]).sum()),
        "postponed_or_cancelled_capacity_mw": round(float(proposed.loc[~proposed["active"], "capacity_mw"].sum()), 1),
        "net_generation_twh": round(float(gen.sum()) / 1e6, 2),
    }

    # Optional cross-check against the EIA-860 workbook
    if args.eia860:
        x = pd.ExcelFile(args.eia860)
        op = pd.read_excel(x, "Operable", skiprows=1)
        op = op[op["State"] == STATE]
        pr = pd.read_excel(x, "Proposed", skiprows=1)
        pr = pr[pr["State"] == STATE]
        checks["eia860_operable_generators"] = int(len(op))
        checks["eia860_operable_capacity_mw"] = round(float(op["Nameplate Capacity (MW)"].sum()), 1)
        checks["eia860_proposed_generators"] = int(len(pr))
        checks["eia860_proposed_capacity_mw"] = round(float(pr["Nameplate Capacity (MW)"].sum()), 1)
        assert checks["eia860_operable_generators"] == checks["existing_generators"]
        assert abs(checks["eia860_operable_capacity_mw"] - checks["existing_capacity_mw"]) < 0.05
        assert checks["eia860_proposed_generators"] == checks["active_proposed_generators"]
        assert abs(checks["eia860_proposed_capacity_mw"] - checks["active_proposed_capacity_mw"]) < 0.05

    (OUT / "checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
