# High Plains Open Energy Data

Open, checked data on the energy system of Wyoming and the High Plains, an independent tracker of what is being
built and retired, and teaching material that helps people use both. The website is published from this
repository at https://high-plains-open-energy-data.github.io.

The project is independent and is not affiliated with any utility, energy company or government agency.

## Contents

| Path | What it holds |
|---|---|
| `index.html`, `data.html`, `monitor.html`, `teaching.html` | The website pages |
| `data/` | Wyoming datasets for 2025, as CSV, plus `checks.json` |
| `teaching/` | The Wyoming electricity lesson: notebook, worksheet and teacher notes |
| `scripts/build_wyoming_data.py` | Builds the datasets from PUDL and cross-checks them against EIA-860 |
| `scripts/build_pages.py` | Builds the website pages from the datasets |

## Rebuilding

```
pip install pandas pyarrow openpyxl
python scripts/build_wyoming_data.py --eia860 path/to/3_1_Generator_Y2025.xlsx
python scripts/build_pages.py
```

The `--eia860` option is optional; it repeats the cross-check against the EIA-860 workbook, which is part of
EIA's annual data release at https://www.eia.gov/electricity/data/eia860/.

## Sources and licence

Data are derived from the [Public Utility Data Liberation project (PUDL)](https://catalyst.coop/pudl/),
Catalyst Cooperative, licensed under CC-BY-4.0, which processes data reported to the U.S. Energy Information
Administration. Text, data and teaching material here are licensed under CC-BY-4.0 (see `LICENSE`); code is
licensed under the MIT licence (see `LICENSE-CODE`).

To report an error or suggest a dataset, please open an issue.
