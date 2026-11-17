"""Check whether PUDL has published a new stable release since the data were last built.

Usage:
    python scripts/check_pudl_release.py          # prints "changed" or "unchanged"
    python scripts/check_pudl_release.py --write  # records the current release in data/pudl_release.json

PUDL's stable release is served from a fixed address; the Last-Modified time of each table changes when a new
release is published. Comparing those times with the ones recorded at the last build tells us whether to rebuild.
"""
import argparse
import email.utils
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RECORD = ROOT / "data" / "pudl_release.json"
PUDL = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/stable/{}.parquet"
TABLES = ["out_eia__yearly_generators", "out_eia923__yearly_generation_fuel_combined", "core_eia861__yearly_sales",
          "out_eia923__monthly_generation_fuel_combined"]


def current():
    stamps = {}
    for t in TABLES:
        req = urllib.request.Request(PUDL.format(t), method="HEAD")
        with urllib.request.urlopen(req) as r:
            stamps[t] = r.headers["Last-Modified"]
    return stamps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    now = current()
    if args.write:
        newest = max(email.utils.parsedate_to_datetime(v) for v in now.values())
        RECORD.write_text(json.dumps({"tables": now,
                                      "pudl_stable_last_modified": f"{newest.day} {newest:%B %Y}"}, indent=2) + "\n")
        print("recorded")
        return
    old = json.loads(RECORD.read_text())["tables"] if RECORD.exists() else {}
    print("changed" if old != now else "unchanged")


if __name__ == "__main__":
    main()
