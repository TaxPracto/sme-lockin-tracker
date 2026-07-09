#!/usr/bin/env python3
"""
One-shot historical price backfill (re-runnable; skips days already stored).
Downloads BSE + NSE UDiFF bhavcopies from START date to today and stores
close+volume for tracked ISINs in data/history.json:
  {"days": {"YYYY-MM-DD": 1}, "series": {isin: {"YYYY-MM-DD": [close, vol]}}}
Feeds outcomes.py (backtest) — never embedded in the webpage.
"""
import csv
import datetime as dt
import io
import json
import os
import time
import zipfile

import requests

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
      "Accept": "*/*", "Referer": "https://www.nseindia.com/"}
BSE = "https://www.bseindia.com/download/BhavCopy/Equity/BhavCopy_BSE_CM_0_0_0_{d}_F_0000.CSV"
NSE = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d}_F_0000.csv.zip"
START = dt.date(2024, 6, 1)


def tracked_isins():
    with open("data/lockins.json", encoding="utf-8") as f:
        recs = json.load(f)["records"]
    return {str(r["isin"]).strip() for r in recs if r.get("isin")}


def parse_udiff(text, isins):
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
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


def main():
    isins = tracked_isins()
    path = "data/history.json"
    hist = {"days": {}, "series": {}}
    if os.path.exists(path):
        try:
            hist = json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    days, series = hist.setdefault("days", {}), hist.setdefault("series", {})
    today = dt.date.today()
    d = START
    fetched = 0
    t0 = time.time()
    while d <= today:
        ds = d.isoformat()
        if d.weekday() >= 5 or ds in days:
            d += dt.timedelta(days=1)
            continue
        dd = d.strftime("%Y%m%d")
        got = {}
        for name, url, is_zip in (("BSE", BSE.format(d=dd), False), ("NSE", NSE.format(d=dd), True)):
            try:
                r = requests.get(url, headers=UA, timeout=40)
                if r.status_code != 200 or len(r.content) < 500:
                    continue
                text = (zipfile.ZipFile(io.BytesIO(r.content)).read(
                        zipfile.ZipFile(io.BytesIO(r.content)).namelist()[0]).decode("utf-8", "ignore")
                        if is_zip else r.text)
                for k, v in parse_udiff(text, isins).items():
                    if k not in got or name == "NSE":
                        got[k] = v
            except Exception as ex:  # noqa: BLE001
                print(f"[backfill] {name} {ds}: {ex}")
        days[ds] = 1 if got else 0     # 0 = holiday/no data, don't retry
        for isin, (close, vol) in got.items():
            series.setdefault(isin, {})[ds] = [close, vol]
        fetched += 1
        if fetched % 25 == 0:
            print(f"[backfill] {ds}: {len(got)} matches | {fetched} days | {int(time.time()-t0)}s")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(hist, f)                 # checkpoint
        time.sleep(0.25)
        d += dt.timedelta(days=1)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hist, f)
    print(f"[backfill] done: {sum(1 for v in days.values() if v)} trading days, "
          f"{len(series)} ISINs with data, {int(time.time()-t0)}s")


if __name__ == "__main__":
    main()
