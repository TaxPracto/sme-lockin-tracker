#!/usr/bin/env python3
"""
Daily price & volume feed for tracked ISINs.
Sources: BSE + NSE official UDiFF bhavcopies (free, no auth).
Maintains data/prices.json = {"updated": date, "hist": {isin: [[date, close, volume], ...]}}
Never crashes the pipeline: partial data is fine, failures are logged.
"""
import csv
import datetime as dt
import io
import json
import os
import zipfile
from zoneinfo import ZoneInfo

import requests

IST = ZoneInfo("Asia/Kolkata")
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
      "Accept": "*/*", "Referer": "https://www.nseindia.com/"}
BSE = "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{d}_F_0000.CSV"
NSE = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d}_F_0000.csv.zip"
HIST_MAX = 30          # keep last 30 sessions per ISIN
SEED_DAYS = 14         # on first run, walk back this many calendar days to build volume history


def tracked_isins():
    with open("data/lockins.json", encoding="utf-8") as f:
        recs = json.load(f)["records"]
    return {str(r["isin"]).strip() for r in recs if r.get("isin")}


def parse_udiff(text, isins):
    out = {}
    rdr = csv.DictReader(io.StringIO(text))
    for row in rdr:
        isin = (row.get("ISIN") or "").strip()
        if isin not in isins:
            continue
        try:
            close = float(row.get("ClsPric") or 0)
            vol = int(float(row.get("TtlTradgVol") or 0))
        except ValueError:
            continue
        if close > 0:
            out[isin] = (close, vol)
    return out


def fetch_day(day, isins):
    d = day.strftime("%Y%m%d")
    found = {}
    for name, url, is_zip in (("BSE", BSE.format(d=d), False), ("NSE", NSE.format(d=d), True)):
        try:
            r = requests.get(url, headers=UA, timeout=40)
            if r.status_code != 200 or len(r.content) < 500:
                print(f"[prices] {name} {d}: HTTP {r.status_code}")
                continue
            if is_zip:
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    text = z.read(z.namelist()[0]).decode("utf-8", "ignore")
            else:
                text = r.text
            got = parse_udiff(text, isins)
            print(f"[prices] {name} {d}: matched {len(got)} tracked ISINs")
            # NSE wins ties (SME mostly Emerge); merge with existing
            for k, v in got.items():
                if k not in found or name == "NSE":
                    found[k] = v
        except Exception as e:  # noqa: BLE001
            print(f"[prices] {name} {d}: {e}")
    return found


def main():
    isins = tracked_isins()
    print(f"[prices] tracking {len(isins)} ISINs")
    path = "data/prices.json"
    hist = {}
    if os.path.exists(path):
        try:
            hist = json.load(open(path, encoding="utf-8")).get("hist", {})
        except Exception:
            hist = {}

    today = dt.datetime.now(IST).date()
    days = [today - dt.timedelta(days=i) for i in range(0, SEED_DAYS if not hist else 6)]
    days = [d for d in days if d.weekday() < 5]        # skip weekends
    have_dates = {e[0] for h in hist.values() for e in h}
    new_data = 0
    for day in sorted(days):                            # oldest first keeps history ordered
        ds = day.isoformat()
        if ds in have_dates:
            continue
        got = fetch_day(day, isins)
        if not got:
            continue
        new_data += 1
        for isin, (close, vol) in got.items():
            h = hist.setdefault(isin, [])
            if not any(e[0] == ds for e in h):
                h.append([ds, close, vol])
                h.sort(key=lambda e: e[0])
                del h[:-HIST_MAX]

    with open(path, "w", encoding="utf-8") as f:
        json.dump({"updated": today.isoformat(), "hist": hist}, f)
    print(f"[prices] wrote {path}: {len(hist)} ISINs, {new_data} new session(s)")


if __name__ == "__main__":
    main()
