"""Build the website pages from the datasets in data/.

Usage:
    python scripts/build_pages.py

Run scripts/build_wyoming_data.py first. The pages are plain HTML with no build step.
"""
import html
import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AS_OF = "14 November 2026"
ORG = "https://github.com/high-plains-open-energy-data"
REPO = ORG + "/high-plains-open-energy-data.github.io"

FUEL_NAMES = {"coal": "Coal", "wind": "Wind", "gas": "Natural gas", "hydro": "Hydro", "solar": "Solar",
              "other": "Other (incl. batteries)", "oil": "Oil", "nuclear": "Nuclear"}
PAGES = [("index.html", "Home"), ("data.html", "Data"), ("monitor.html", "Monitor"), ("teaching.html", "Teaching")]


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
Administration. Text and data on this site are licensed under
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
<h2>Downloads</h2>
<ul>
<li><a href="data/wyoming_generators_2025.csv">wyoming_generators_2025.csv</a>: all {checks['existing_generators']}
existing generators, with plant, utility, county, coordinates, balancing authority, fuel, technology, status,
capacity and dates.</li>
<li><a href="data/wyoming_capacity_generation_by_fuel_2025.csv">wyoming_capacity_generation_by_fuel_2025.csv</a>:
the summary above.</li>
<li><a href="data/wyoming_proposed_generators_2025.csv">wyoming_proposed_generators_2025.csv</a> and
<a href="data/wyoming_planned_retirements_2025.csv">wyoming_planned_retirements_2025.csv</a>: the data behind the
<a href="monitor.html">monitor</a>.</li>
<li><a href="data/checks.json">checks.json</a>: the totals and cross-checks recorded when the data was built.</li>
</ul>
<h2>Sources</h2>
<ul>
<li>PUDL table <code>out_eia__yearly_generators</code> (EIA Forms 860 and 923): generators, capacity and status.</li>
<li>PUDL table <code>out_eia923__yearly_generation_fuel_combined</code> (EIA Form 923): net generation by plant and
fuel.</li>
<li>EIA-860 2025 data release, file <code>3_1_Generator_Y2025.xlsx</code>, used to cross-check the PUDL figures.</li>
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
<p>Run <code>python scripts/build_wyoming_data.py</code> from the <a href="{REPO}">repository</a>. Add
<code>--eia860 path/to/3_1_Generator_Y2025.xlsx</code> to repeat the cross-check against EIA's release.</p>
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
<h2>Indefinitely postponed or cancelled</h2>
<p>These remain in some datasets with a "proposed" status, which can overstate the capacity in development if they
are not excluded.</p>
{inact_tab}
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
                            ("monitor.html", "Monitor", monitor), ("teaching.html", "Teaching", teaching)]:
        (ROOT / fn).write_text(page(fn, title, body), encoding="utf-8")
    print("pages written")


if __name__ == "__main__":
    main()
