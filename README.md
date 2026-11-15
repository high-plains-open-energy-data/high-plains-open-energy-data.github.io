# High Plains Open Energy Data

Open, checked data on the energy system of Wyoming and the High Plains, an independent tracker of what is being
built and retired, and teaching material that helps people use both. The website is published from this
repository at https://high-plains-open-energy-data.github.io.

The project is independent and is not affiliated with any utility, energy company or government agency.

## Contents

| Path | What it holds |
|---|---|
| `index.html`, `data.html`, `monitor.html`, `transmission.html`, `teaching.html` | The website pages |
| `data/` | The Wyoming datasets, as CSV and JSON, with the checks recorded at each build |
| `teaching/` | The Wyoming electricity lesson: notebook, worksheet and teacher notes |
| `scripts/build_wyoming_data.py` | Builds the 2025 generator, generation and sales datasets from PUDL and cross-checks them against EIA-860 |
| `scripts/build_retirement_history.py` | Builds the history of planned retirement dates for Wyoming's coal units, edition by edition, and checks it against EIA-860 |
| `scripts/build_wyoming_queue.py` | Builds the Wyoming interconnection-queue dataset from Berkeley Lab's Queued Up file and checks it against Berkeley Lab's own state totals |
| `scripts/build_transmission_map.py` | Builds the transmission map and its GeoJSON files from an OpenStreetMap extract of Wyoming's lines and substations |
| `scripts/check_pudl_release.py` | Tells whether PUDL has published a new release since the last build |
| `scripts/build_pages.py` | Builds the website pages from the datasets |
| `.github/workflows/rebuild.yml` | Rebuilds and re-checks the PUDL datasets each week when PUDL publishes a new release |
| `CITATION.cff`, `.zenodo.json` | Citation metadata, used by GitHub and Zenodo |

## Rebuilding

```
pip install pandas pyarrow openpyxl
python scripts/build_wyoming_data.py --eia860 path/to/3_1_Generator_Y2025.xlsx
python scripts/build_retirement_history.py --verify 2023=path/to/3_1_Generator_Y2023.xlsx 2024=path/to/3_1_Generator_Y2024.xlsx 2025=path/to/3_1_Generator_Y2025.xlsx
python scripts/build_wyoming_queue.py --lbnl path/to/LBNL_Ix_Queue_Data_File_thru2025.xlsx
python scripts/check_pudl_release.py --write
python scripts/build_pages.py
```

The `--eia860` and `--verify` options repeat the cross-checks against the EIA-860 workbooks, which are part of
EIA's annual data releases at https://www.eia.gov/electricity/data/eia860/. The Queued Up file is published once a
year by Berkeley Lab at https://emp.lbl.gov/queues.

## Automatic updates

`.github/workflows/rebuild.yml` runs every Monday. If PUDL has published a new release, it rebuilds the PUDL
datasets, repeats every cross-check against EIA's own workbooks, rebuilds the pages and commits the result. If any
check fails, nothing is committed and the workflow fails, so a failed run is the signal to look at the data. It can
also be run by hand from the Actions tab.

## Sources and licence

Data are derived from the [Public Utility Data Liberation project (PUDL)](https://catalyst.coop/pudl/),
Catalyst Cooperative, licensed under CC-BY-4.0, which processes data reported to the U.S. Energy Information
Administration. The interconnection-queue dataset is derived from Berkeley Lab's Queued Up data file (Lawrence
Berkeley National Laboratory and GridTracker), licensed under CC-BY-4.0. The transmission map and the files
`data/wyoming_transmission_lines_osm.geojson` and `data/wyoming_substations_osm.geojson` are derived from
OpenStreetMap (© OpenStreetMap contributors) and are released under the Open Database Licence (ODbL). Text, data and teaching material here are licensed under CC-BY-4.0 (see `LICENSE`); code is
licensed under the MIT licence (see `LICENSE-CODE`).

To cite the project, use the "Cite this repository" button on GitHub or the DOI of the relevant release on Zenodo.

To report an error or suggest a dataset, please open an issue.
