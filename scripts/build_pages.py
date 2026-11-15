"""Build the website pages from the datasets in data/.

Usage:
    python scripts/build_pages.py

Run scripts/build_wyoming_data.py first. The pages are plain HTML with no build step.
"""
import datetime
import html
import json
import os
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
_today = datetime.date.today()
AS_OF = os.environ.get("HPOED_AS_OF", f"{_today.day} {_today:%B %Y}")
ORG = "https://github.com/high-plains-open-energy-data"
REPO = ORG + "/high-plains-open-energy-data.github.io"

FUEL_NAMES = {"coal": "Coal", "wind": "Wind", "gas": "Natural gas", "hydro": "Hydro", "solar": "Solar",
              "other": "Other (incl. batteries)", "oil": "Oil", "nuclear": "Nuclear"}
PAGES = [("index.html", "Home"), ("data.html", "Data"), ("monitor.html", "Monitor"),
         ("transmission.html", "Transmission"), ("teaching.html", "Teaching")]


def esc(x):
    return html.escape(str(x))


def mw(x):
    return f"{x:,.1f}"


def page(filename, title, body):
    current = ' class="current"'
    nav = "".join(
        f'<a href="{f}"{current if f == filename else ""}>{esc(n)}</a>' for f, n in PAGES)
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | High Plains Open Energy Data</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header>
<a class="name" href="index.html">High Plains Open Energy Data</a>
<nav>{nav}</nav>
</header>
<main>
{body}
</main>
<footer>
<p>High Plains Open Energy Data is an independent project. It is not affiliated with any utility, energy company
or government agency, including any organisation with "High Plains" in its name.</p>
<p>Data derived from the <a href="https://catalyst.coop/pudl/">Public Utility Data Liberation project (PUDL)</a>,
Catalyst Cooperative, licensed under CC-BY-4.0, which processes data reported to the U.S. Energy Information
Administration. Interconnection-queue data from Berkeley Lab's <a href="https://emp.lbl.gov/queues">Queued Up</a>
data file (Lawrence Berkeley National Laboratory and GridTracker), licensed under CC-BY-4.0. Transmission map
data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>, under the ODbL.
Text and data on this site are licensed under
<a href="https://creativecommons.org/licenses/by/4.0/">CC-BY-4.0</a>; code under the MIT licence.
<a href="{REPO}">Source on GitHub</a>.</p>
</footer>
</body>
</html>
"""


def table(df, cols, num=()):
    numcls = ' class="num"'
    head = "".join(f'<th{numcls if c in num else ""}>{esc(lbl)}</th>' for c, lbl in cols)
    rows = []
    for _, r in df.iterrows():
        cells = []
        for c, _ in cols:
            v = r[c]
            v = "" if pd.isna(v) else v
            cells.append(f'<td{numcls if c in num else ""}>{esc(v)}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def main():
    checks = json.loads((DATA / "checks.json").read_text())
    summary = pd.read_csv(DATA / "wyoming_capacity_generation_by_fuel_2025.csv")
    proposed = pd.read_csv(DATA / "wyoming_proposed_generators_2025.csv")
    retiring = pd.read_csv(DATA / "wyoming_planned_retirements_2025.csv")
    balance = pd.read_csv(DATA / "wyoming_generation_and_sales.csv")
    queue = json.loads((DATA / "wyoming_queue_summary.json").read_text())
    rchecks = json.loads((DATA / "retirement_history_checks.json").read_text())
    rwide = pd.read_csv(DATA / "wyoming_coal_planned_retirement_by_edition.csv")
    rhist = pd.read_csv(DATA / "wyoming_coal_retirement_history.csv")
    tx = json.loads((DATA / "wyoming_transmission_summary.json").read_text())
    release = json.loads((DATA / "pudl_release.json").read_text()) if (DATA / "pudl_release.json").exists() else {}

    # ---------- Home ----------
    home = f"""
<h1>Open, checked data on the energy system of Wyoming and the High Plains</h1>
<p class="lead">High Plains Open Energy Data publishes verified public data on electricity generation and
transmission, tracks what is being built and retired, and provides teaching material that helps people use both.
It starts with Wyoming.</p>
<div class="cards">
<div class="card"><h3><a href="data.html">Data</a></h3>Datasets built from public sources, with every figure
checked against its original source and every step documented so it can be reproduced.</div>
<div class="card"><h3><a href="monitor.html">Monitor</a></h3>An independent tracker of the generating capacity
proposed, under construction and planned for retirement in the region, with a source for every entry.</div>
<div class="card"><h3><a href="transmission.html">Transmission</a></h3>A map of Wyoming's power lines
and substations at 69 kV and above, built from public data, with the data to download.</div>
<div class="card"><h3><a href="teaching.html">Teaching</a></h3>Lessons and notebooks that use the same data,
for students, teachers and anyone who wants to understand the region's energy system.</div>
</div>
<h2>Why the High Plains</h2>
<p>Wyoming produces far more electricity than it uses, and the region's generation, transmission and coal
transition matter well beyond its borders. Much of the public data that describes them is scattered across federal
forms and hard to use. This project brings it together for Wyoming first, checks it, and explains it in plain
language for journalists, legislators, local governments, students and anyone taking part in decisions about
energy projects.</p>
<h2>Independence</h2>
<p>The project is independent. It is not affiliated with any utility, energy company or government agency, and it
takes no position for or against any project. Its aim is accurate public information.</p>
<h2>Built on open data</h2>
<p>The datasets are built on the <a href="https://catalyst.coop/pudl/">Public Utility Data Liberation project
(PUDL)</a>, maintained by Catalyst Cooperative, and checked against the original U.S. Energy Information
Administration (EIA) releases. Corrections that belong upstream are reported to PUDL.</p>
<h2>Contact</h2>
<p>Maintained by Noah Parsons, Newcastle, Wyoming. To report an error or suggest a dataset, please
<a href="{REPO}/issues">open an issue on GitHub</a>.</p>
<p class="asof">As of {AS_OF}.</p>
"""
    # ---------- Data ----------
    s = summary.copy()
    s["fuel"] = s["fuel_type_code_pudl"].map(FUEL_NAMES)
    s["cap"] = s["capacity_mw"].map(mw)
    s["gen"] = (s["net_generation_mwh"] / 1e6).map(lambda x: f"{x:.2f}")
    s["cs"] = s["capacity_share_pct"].map(lambda x: f"{x:.1f}%")
    s["gs"] = s["generation_share_pct"].map(lambda x: f"{x:.1f}%")
    tot = pd.DataFrame([{"fuel": "Total", "generators": int(s["generators"].sum()),
                         "cap": mw(checks["existing_capacity_mw"]), "cs": "100%",
                         "gen": f"{checks['net_generation_twh']:.2f}", "gs": "100%"}])
    s = pd.concat([s, tot])
    sum_tab = table(s, [("fuel", "Fuel"), ("generators", "Generators"), ("cap", "Capacity (MW)"),
                        ("cs", "Share of capacity"), ("gen", "2025 net generation (TWh)"),
                        ("gs", "Share of generation")],
                    num={"generators", "cap", "cs", "gen", "gs"})
    bal = balance[balance["year"].isin([2001, 2005, 2010, 2015, 2020, 2024, 2025])].copy()
    bal["gen"] = (bal["net_generation_mwh"] / 1e6).map(lambda x: f"{x:.1f}")
    bal["sales"] = (bal["retail_sales_mwh"] / 1e6).map(lambda x: f"{x:.1f}")
    bal["share"] = bal["net_export_share_pct"].map(lambda x: f"{x:.0f}%")
    bal_tab = table(bal, [("year", "Year"), ("gen", "Net generation (TWh)"), ("sales", "In-state retail sales (TWh)"),
                          ("share", "Not sold in Wyoming")], num={"gen", "sales", "share"})
    data = f"""
<h1>Wyoming electricity generation, 2025</h1>
<p class="asof">Dataset as of {AS_OF}. Covers generators located in Wyoming as reported to EIA for 2025, the most
recent year of final data.</p>
<h2>Summary by fuel</h2>
{sum_tab}
<p>Coal provided about {summary.loc[summary.fuel_type_code_pudl=='coal','generation_share_pct'].iloc[0]:.0f}% of
Wyoming's 2025 generation from {summary.loc[summary.fuel_type_code_pudl=='coal','capacity_share_pct'].iloc[0]:.0f}%
of its capacity; wind provided about
{summary.loc[summary.fuel_type_code_pudl=='wind','generation_share_pct'].iloc[0]:.0f}% from
{summary.loc[summary.fuel_type_code_pudl=='wind','capacity_share_pct'].iloc[0]:.0f}%.</p>
<h2>Where it goes: generation and in-state sales, 2001 to 2025</h2>
<p>Comparing the electricity generated in Wyoming with the electricity sold to retail customers in Wyoming gives a
rough measure of how much leaves the state. In 2025, {checks['net_export_share_pct']:.0f}% of Wyoming's net
generation was not sold to Wyoming customers. The share has drifted down from about 71% in 2001, mainly because
in-state sales grew while generation stayed roughly level.</p>
{bal_tab}
<p>This is a net, approximate figure. It does not account for transmission and distribution losses, for electricity
imported into Wyoming, or for which plants serve which customers. Delivery-only sales are excluded, because
the same energy also appears as an energy sale; in Wyoming all reported sales are bundled, so this makes no
difference here.</p>
<h2>Downloads</h2>
<ul>
<li><a href="data/wyoming_generators_2025.csv">wyoming_generators_2025.csv</a>: all {checks['existing_generators']}
existing generators, with plant, utility, county, coordinates, balancing authority, fuel, technology, status,
capacity and dates.</li>
<li><a href="data/wyoming_capacity_generation_by_fuel_2025.csv">wyoming_capacity_generation_by_fuel_2025.csv</a>:
the summary above.</li>
<li><a href="data/wyoming_generation_and_sales.csv">wyoming_generation_and_sales.csv</a>: net generation,
in-state retail sales and the share not sold in Wyoming, for each year from 2001 to 2025.</li>
<li><a href="data/wyoming_proposed_generators_2025.csv">wyoming_proposed_generators_2025.csv</a> and
<a href="data/wyoming_planned_retirements_2025.csv">wyoming_planned_retirements_2025.csv</a>: the data behind the
<a href="monitor.html">monitor</a>.</li>
<li><a href="data/wyoming_interconnection_queue.csv">wyoming_interconnection_queue.csv</a>: all
{queue['requests']} interconnection requests in Wyoming in Berkeley Lab's Queued Up data, with status, study
phase, technology, size and dates; summarised in <a href="data/wyoming_queue_summary.json">wyoming_queue_summary.json</a>.</li>
<li><a href="data/wyoming_coal_retirement_history.csv">wyoming_coal_retirement_history.csv</a>: every Wyoming
generator that has burned coal, in every EIA-860 edition from {rchecks['first_edition']} to
{rchecks['last_edition']}, with its fuel, status and planned retirement date; and
<a href="data/wyoming_coal_planned_retirement_by_edition.csv">wyoming_coal_planned_retirement_by_edition.csv</a>,
one row per unit that has ever reported a planned retirement date.</li>
<li><a href="data/checks.json">checks.json</a> and <a href="data/retirement_history_checks.json">retirement_history_checks.json</a>:
the totals and cross-checks recorded when the data was built.</li>
</ul>
<h2>Sources</h2>
<ul>
<li>PUDL table <code>out_eia__yearly_generators</code> (EIA Forms 860 and 923): generators, capacity and status.</li>
<li>PUDL table <code>out_eia923__yearly_generation_fuel_combined</code> (EIA Form 923): net generation by plant and
fuel.</li>
<li>PUDL table <code>core_eia861__yearly_sales</code> (EIA Form 861): retail sales by utility and state.</li>
<li>EIA-860 data releases, file <code>3_1_Generator_Y2025.xlsx</code> and its 2023 and 2024 equivalents, used to
cross-check the PUDL figures.</li>
<li>Berkeley Lab, <em>Queued Up</em> 2026 Edition data file, interconnection requests through the end of 2025.</li>
</ul>
<h2>Checks</h2>
<p>Every build compares the PUDL figures with the EIA-860 workbook itself. For 2025:</p>
<ul>
<li>Existing generators: {checks['existing_generators']} generators and {mw(checks['existing_capacity_mw'])} MW in
PUDL, against {checks.get('eia860_operable_generators','n/a')} generators and
{mw(checks.get('eia860_operable_capacity_mw',0))} MW on EIA-860's operable schedule. They match exactly.</li>
<li>Active proposed generators: {checks['active_proposed_generators']} generators and
{mw(checks['active_proposed_capacity_mw'])} MW in PUDL, against {checks.get('eia860_proposed_generators','n/a')}
generators and {mw(checks.get('eia860_proposed_capacity_mw',0))} MW on EIA-860's proposed schedule. They match
exactly once indefinitely postponed and cancelled projects are excluded, as described on the
<a href="monitor.html">monitor</a> page.</li>
</ul>
<li>Planned retirement dates: for the {rchecks['units']} Wyoming units that have burned coal, the planned
retirement month and year in PUDL were compared with EIA's own workbooks for
{', '.join(sorted(rchecks['verified_against_eia']))}; all match.</li>
<li>Interconnection queue: the active capacity computed here for gas, solar and wind matches, to the megawatt, the
Wyoming totals that Berkeley Lab publishes in the same file
({', '.join(f"{t} {v:.2f} GW" for t, v in queue['checks']['active_gw_published_by_lbnl'].items())}).</li>
</ul>
<h2>Notes and limitations</h2>
<ul>
<li>Capacity is nameplate capacity. Summer and winter capacities, which are usually lower, are included in the
generator file.</li>
<li>Generation by fuel comes from plant-level EIA-923 data. Each generator has one primary fuel code, so units that
can burn more than one fuel, or that have been converted, are counted under their primary fuel.</li>
<li>"Other" includes battery storage and small units reporting other fuels.</li>
<li>Net generation is measured at the plant; it is not the same as electricity consumed in Wyoming.</li>
</ul>
<h2>Reproduce it</h2>
<p>Run <code>python scripts/build_wyoming_data.py</code>, <code>python scripts/build_retirement_history.py</code>
and <code>python scripts/build_wyoming_queue.py --lbnl path/to/LBNL_Ix_Queue_Data_File_thru2025.xlsx</code> from
the <a href="{REPO}">repository</a>. Add <code>--eia860 path/to/3_1_Generator_Y2025.xlsx</code> to the first, and
<code>--verify 2025=path/to/3_1_Generator_Y2025.xlsx</code> to the second, to repeat the cross-checks against
EIA's release.</p>
<p>The datasets built from PUDL are rebuilt automatically when PUDL publishes a new release, and are published only
if every check passes.{(" Current PUDL release: published " + release['pudl_stable_last_modified'] + ".") if release else ""}</p>
<h2>Licence and attribution</h2>
<p>CC-BY-4.0. Please cite as: High Plains Open Energy Data (2026), <em>Wyoming electricity generation, 2025</em>,
derived from the Public Utility Data Liberation project (Catalyst Cooperative) and U.S. EIA Form 860 and 923
data.</p>
"""
    # ---------- Monitor ----------
    act = proposed[proposed["active"]].copy()
    inact = proposed[~proposed["active"]].copy()
    for d in (act, inact):
        d["cap"] = d["capacity_mw"].map(mw)
        d["planned"] = pd.to_datetime(d["current_planned_generator_operating_date"]).dt.strftime("%b %Y")
        d["status"] = d["operational_status_code"]
    by_type = act.groupby("technology_description")["capacity_mw"].sum().sort_values(ascending=False)
    type_list = "".join(f"<li>{esc(t)}: {mw(v)} MW</li>" for t, v in by_type.items())
    uc = act[act["operational_status_code"].isin(["U", "V", "TS"])]["capacity_mw"].sum()
    retiring["cap"] = retiring["capacity_mw"].map(mw)
    retiring["date"] = pd.to_datetime(retiring["planned_generator_retirement_date"]).dt.strftime("%b %Y")
    act_tab = table(act, [("plant_name_eia", "Plant"), ("generator_id", "Generator"),
                          ("technology_description", "Technology"), ("cap", "Capacity (MW)"),
                          ("county", "County"), ("utility_name_eia", "Owner or operator"),
                          ("status", "Status"), ("planned", "Planned operation"),
                          ("plant_id_eia", "EIA plant ID")], num={"cap", "plant_id_eia"})
    ret_tab = table(retiring, [("plant_name_eia", "Plant"), ("generator_id", "Generator"),
                               ("technology_description", "Technology"), ("cap", "Capacity (MW)"),
                               ("utility_name_eia", "Operator"), ("date", "Planned retirement"),
                               ("plant_id_eia", "EIA plant ID")], num={"cap", "plant_id_eia"})
    inact_tab = table(inact, [("plant_name_eia", "Plant"), ("generator_id", "Generator"),
                              ("technology_description", "Technology"), ("cap", "Capacity (MW)"),
                              ("county", "County"), ("status", "Status"),
                              ("plant_id_eia", "EIA plant ID")], num={"cap", "plant_id_eia"})
    # Planned retirement dates by EIA-860 edition (recent editions only in the table; all are in the CSV)
    rw = rwide.copy()
    recent = [c for c in rw.columns if c.isdigit() and int(c) >= 2019]
    rw = rw[rw[recent].notna().any(axis=1)]
    for c in recent:
        rw[c] = pd.to_datetime(rw[c], format="%Y-%m", errors="coerce").dt.strftime("%b %Y").fillna("none")
    rw["unit"] = rw["plant_name_eia"] + " " + rw["generator_id"].astype(str)
    hist = rhist.copy()
    cap23 = hist[hist["year"] == 2023].set_index(["plant_id_eia", "generator_id"])
    cap24 = hist[hist["year"] == 2024].set_index(["plant_id_eia", "generator_id"])
    gone = cap23[cap23["planned_generator_retirement_date"].notna()].index.difference(
        cap24[cap24["planned_generator_retirement_date"].notna()].index)
    gone_coal = [k for k in gone if cap23.loc[k, "fuel_type_code_pudl"] == "coal"]
    gone_mw = cap23.loc[gone_coal, "capacity_mw"].sum()
    drift_tab = table(rw, [("unit", "Unit")] + [(c, c) for c in recent])
    # Interconnection queue
    qs = queue["by_status"]
    q_status = pd.DataFrame([{"status": k.capitalize(), "count": v["count"], "mw": mw(v["sum"])}
                             for k, v in sorted(qs.items(), key=lambda kv: -kv[1]["count"])])
    q_status_tab = table(q_status, [("status", "Status"), ("count", "Requests"), ("mw", "Capacity (MW)")],
                         num={"count", "mw"})
    q_type = pd.DataFrame([{"type": k, "count": v["count"], "mw": mw(v["sum"])}
                           for k, v in queue["active_by_type"].items()])
    q_type_tab = table(q_type, [("type", "Technology (first resource)"), ("count", "Active requests"),
                                ("mw", "Capacity (MW)")], num={"count", "mw"})
    q_phase = pd.DataFrame([{"phase": k, "count": v["count"], "mw": mw(v["sum"])}
                            for k, v in queue["active_by_phase"].items()])
    q_phase_tab = table(q_phase, [("phase", "Study phase"), ("count", "Active requests"), ("mw", "Capacity (MW)")],
                        num={"count", "mw"})
    q_cov = pd.DataFrame([{"entity": k, "dated": v["dated"], "total": v["total"]}
                          for k, v in queue["withdrawal_date_coverage"].items()])
    q_cov_tab = table(q_cov, [("entity", "Queue operator"), ("total", "Withdrawn requests"),
                              ("dated", "With a withdrawal date")], num={"dated", "total"})
    early = queue["requests_entered_2020_or_earlier"]
    early_n = sum(v["count"] for v in early.values())
    early_op = early.get("operational", {}).get("count", 0)
    early_wd = early.get("withdrawn", {}).get("count", 0)
    q_active = qs["active"]
    q_wd = qs["withdrawn"]
    q_ia = queue["active_by_phase"].get("IA Executed", {"count": 0, "sum": 0})
    monitor = f"""
<h1>Wyoming generation tracker</h1>
<p class="asof">As of {AS_OF}. Statuses are as reported to EIA for 31 December 2025 in the EIA-860 2025 data
release, the most recent final data. They will be updated when EIA publishes newer data.</p>
<h2>Summary</h2>
<p>For 2025, developers and utilities reported <strong>{checks['active_proposed_generators']} active proposed
generators</strong> in Wyoming, totalling <strong>{mw(checks['active_proposed_capacity_mw'])} MW</strong>, against
{mw(checks['existing_capacity_mw'])} MW of existing capacity. Of that, {mw(uc)} MW was under construction.</p>
<ul>{type_list}</ul>
<p>A further {checks['postponed_or_cancelled_generators']} generators ({mw(checks['postponed_or_cancelled_capacity_mw'])}
MW) were reported as indefinitely postponed or cancelled, and are listed separately below. Two existing generators
report a planned retirement.</p>
<h2>Active proposed generators</h2>
{act_tab}
<h2>Planned retirements</h2>
{ret_tab}
<h2>How planned coal retirement dates have changed</h2>
<p>EIA-860 records, each year, the retirement date that a plant's owner plans for each generator. Comparing the
annual editions shows how those plans have moved. Between the 2023 and 2024 editions, {len(gone_coal)} Wyoming coal
units totalling {mw(gone_mw)} MW stopped reporting a planned retirement date: Dave Johnston 1, 2 and 4, Jim Bridger
1 to 4, Naughton 1 and 2, and Wyodak. Only Dave Johnston 3 kept its date, December 2027. Two of the units, Jim Bridger 1 and 2, had been converted to burn natural
gas by the 2024 edition.</p>
{drift_tab}
<p>"None" means that edition reported no planned retirement date for the unit. The table shows the editions from
2019; earlier editions, back to {rchecks['first_edition']}, are in the
<a href="data/wyoming_coal_retirement_history.csv">full history</a>. The only earlier planned dates are for Neil
Simpson 5 and Osage 1 to 3, which reported March 2014 in the 2011 to 2013 editions and retired that month. Naughton 3
burned coal until its conversion to natural gas and is included for that reason. A missing date records what the
owner reported to EIA; the form does not say why a date was added or removed. Every date shown for 2023, 2024 and
2025 was checked against EIA's own workbook.</p>
<h2>Indefinitely postponed or cancelled</h2>
<p>These remain in some datasets with a "proposed" status, which can overstate the capacity in development if they
are not excluded.</p>
{inact_tab}
<h2>Interconnection queue</h2>
<p>Before a generator can connect to the grid, its developer must request interconnection from the transmission
provider and pass through a series of studies. Berkeley Lab's <em>Queued Up</em> data file gathers these requests
from every queue in the country. It lists <strong>{queue['requests']} requests</strong> for projects in Wyoming,
covering requests through the end of 2025.</p>
{q_status_tab}
<p>At the end of 2025, {q_active['count']} requests for {mw(q_active['sum'])} MW were active: {q_active['sum'] / checks['existing_capacity_mw']:.1f} times Wyoming's
existing capacity of {mw(checks['existing_capacity_mw'])} MW, and {q_active['sum'] / checks['active_proposed_capacity_mw']:.1f}
times the {mw(checks['active_proposed_capacity_mw'])} MW of proposed generators reported to EIA. A queue request is an early
step, not a plan to build: {q_ia['count']} of the active requests ({mw(q_ia['sum'])} MW) had signed an
interconnection agreement. Of the {early_n} Wyoming requests entered in 2020 or earlier, {early_op}
({100 * early_op / early_n:.0f}%) reached commercial operation and {early_wd} ({100 * early_wd / early_n:.0f}%)
were withdrawn.</p>
<h3>Active requests by technology</h3>
{q_type_tab}
<h3>Active requests by study phase</h3>
{q_phase_tab}
<h3>When requests are withdrawn</h3>
<p>Of the {q_wd['count']} withdrawn requests, only {queue['withdrawn_with_date']}
({100 * queue['withdrawn_with_date'] / q_wd['count']:.0f}%) carry a withdrawal date, almost all of them from
PacifiCorp. For those {queue['withdrawn_with_date']}, the median time from request to withdrawal was
{queue['median_years_request_to_withdrawal_dated']} years, but so few are dated that the figure cannot be taken to
represent Wyoming's queue as a whole.</p>
{q_cov_tab}
<p>Notes: figures count interconnection requests, not projects; one project can file more than one request, or
file in more than one queue. Capacity is the first resource's size, so the storage part of a hybrid project is not
added. The active capacity computed here for gas, solar and wind matches the Wyoming totals that Berkeley Lab
publishes in the same file. Download: <a href="data/wyoming_interconnection_queue.csv">all {queue['requests']}
requests</a>.</p>
<h2>Reading this tracker</h2>
<ul>
<li>Every entry comes from EIA Form 860, as processed by PUDL and checked against EIA's own release. The EIA plant
ID links each row to EIA's records.</li>
<li>Proposed projects and dates are reported by their developers. Many proposed projects are delayed or never built,
and planned dates often move.</li>
<li>Status codes show each generator's status on 31 December 2025, using EIA's definitions: P, planned with regulatory approvals not initiated; L, approvals pending;
T, approvals received; U and V, under construction (up to and above half complete); TS, built but not yet in
commercial operation; IP, indefinitely postponed; CN, cancelled.</li>
<li>Battery storage paired with a solar project is listed as its own generator, as EIA reports it.</li>
</ul>
<p>Download the data: <a href="data/wyoming_proposed_generators_2025.csv">proposed generators</a>,
<a href="data/wyoming_planned_retirements_2025.csv">planned retirements</a>.</p>
"""
    # ---------- Transmission ----------
    tx_rows = pd.DataFrame([{"cls": k, "km": f"{v:,}"} for k, v in tx["km_by_voltage_class"].items()]
                           + [{"cls": "Total", "km": f"{tx['km_total']:,}"}])
    tx_rows["cls"] = tx_rows["cls"].replace({"untagged": "Voltage not tagged"})
    tx_tab = table(tx_rows, [("cls", "Voltage"), ("km", "Length in Wyoming (km)")], num={"km"})
    transmission = f"""
<h1>Wyoming's transmission network</h1>
<p class="asof">Map data as of {tx['osm_date']}.</p>
<p>A map of the power lines and substations in Wyoming at 69 kV and above, built entirely from public data. The
lines and substations come from <a href="https://www.openstreetmap.org/">OpenStreetMap</a>, which volunteers map
and which is detailed in Wyoming, though neither complete nor official.</p>
<p><a href="assets/wyoming_transmission_map.png"><img src="assets/wyoming_transmission_map.png"
alt="Map of Wyoming's transmission lines by voltage, with substations and the main towns" style="width:100%"></a></p>
<h2>Line length by voltage</h2>
{tx_tab}
<p>The map shows {tx['lines']:,} line sections and {tx['substations']} substations. Lengths are measured inside
Wyoming only; lines that cross the state line are cut at the border. About {tx['km_by_voltage_class'].get('untagged', 0):,}
km of lines carry no voltage in OpenStreetMap and are drawn as dashed grey lines.</p>
<h2>Downloads</h2>
<ul>
<li><a href="data/wyoming_transmission_lines_osm.geojson">wyoming_transmission_lines_osm.geojson</a>: every line
section, with its OpenStreetMap ID, name, operator, voltage tag, voltage class, the counties it crosses and its
length in Wyoming.</li>
<li><a href="data/wyoming_substations_osm.geojson">wyoming_substations_osm.geojson</a>: every substation, with its
OpenStreetMap ID, name, operator, voltage tag and county.</li>
<li><a href="assets/wyoming_transmission_map.png">The map above</a>, as an image.</li>
</ul>
<p>GitHub displays GeoJSON files as an interactive map: open either file in the
<a href="{REPO}/tree/main/data">repository</a> to zoom in and click on any line or substation.</p>
<h2>Licence</h2>
<p>Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>, available
under the Open Database Licence (ODbL). The two GeoJSON files are derived from OpenStreetMap and are released under
the <a href="https://opendatacommons.org/licenses/odbl/">ODbL</a>, not under this site's CC-BY-4.0 licence.
County boundaries are from the U.S. Census Bureau's cartographic boundary files.</p>
<p>Corrections to lines or voltages are best made in OpenStreetMap itself, where they benefit everyone; they will
appear here when the map is next rebuilt.</p>
"""
    # ---------- Teaching ----------
    teaching = f"""
<h1>Teaching</h1>
<h2>Where does Wyoming's electricity come from, and where does it go?</h2>
<p>An undergraduate lesson, about 90 minutes, built on the same open data as this site. Students load three PUDL
tables, compare capacity with generation, find the coal units converted to natural gas, estimate how much of
Wyoming's electricity leaves the state, and look at what is proposed.</p>
<ul>
<li><a href="teaching/wyoming-electricity-with-pudl.ipynb">Jupyter notebook</a> (Python, pandas, pyarrow,
matplotlib)</li>
<li><a href="teaching/wyoming-electricity-worksheet.docx">Student worksheet</a> (Word)</li>
<li><a href="teaching/wyoming-electricity-teacher-notes.docx">Teacher notes with answers</a> (Word)</li>
</ul>
<p><strong>Level:</strong> first- or second-year undergraduates in engineering, environmental science, economics or
data science. <strong>Prerequisites:</strong> basic Python and pandas.</p>
<p class="note">The notebook reads PUDL's current "stable" release. The answers in the teacher notes come from the
release published on 10 November 2026, so later releases may change some figures slightly.</p>
<p>Teachers who use the lesson are warmly invited to <a href="{REPO}/issues">open an issue</a> with feedback.</p>
<p class="asof">As of {AS_OF}.</p>
"""
    for fn, title, body in [("index.html", "Home", home), ("data.html", "Data", data),
                            ("monitor.html", "Monitor", monitor), ("transmission.html", "Transmission", transmission),
                            ("teaching.html", "Teaching", teaching)]:
        (ROOT / fn).write_text(page(fn, title, body), encoding="utf-8")
    print("pages written")


if __name__ == "__main__":
    main()
