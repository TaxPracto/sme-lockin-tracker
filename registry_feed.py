#!/usr/bin/env python3
"""
Anchor registry from Chittorgarh's anchor reports (SME variant):
  report 133 -> fund houses per year        (id via /190/sme/{id}/)
  report 190 -> schemes of a house          (id via /134/sme/{id}/)
  report 134 -> a scheme's IPO deals        (slug, shares, invested, listing gain)
Writes data/registry.json:
  {"updated":..., "houses": {house: {"deals": {slug: {"inv": cr, "sh": n, "lg": %, "cg": %}},
                                     "years": {"2026": n_issues}}}}
Incremental: a (house, year) is refetched only when its issue count changes.
"""
import datetime as dt
import json
import os
import re
import time

import requests

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
      "Referer": "https://www.chittorgarh.com/report/anchor-investors-list/133/sme/",
      "Accept": "application/json"}
API = "https://webnodejs.chittorgarh.com/cloud/report/data-read/{rep}/1/2/{year}/{fy}/0/sme/{ent}"
ID_190 = re.compile(r"/190/sme/(\d+)/")
ID_134 = re.compile(r"/134/sme/(\d+)/")
TITLE = re.compile(r'title="([^"]+)"')
PCT = re.compile(r"\(([-\d.]+)%\)")


def fetch(rep, year, ent=0):
    fy = f"{year}-{str(year + 1)[-2:]}"
    url = API.format(rep=rep, year=year, fy=fy, ent=ent) + f"?search=&v={dt.datetime.now().strftime('%H-%M')}"
    for attempt in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            return r.json().get("reportTableData") or []
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                print(f"[registry] {rep}/{year}/{ent}: {e}")
                return []
            time.sleep(4)
    return []


def main():
    today = dt.date.today()
    years = [today.year - 2, today.year - 1, today.year]
    path = "data/registry.json"
    reg = {"houses": {}}
    if os.path.exists(path):
        try:
            reg = json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    houses = reg.setdefault("houses", {})
    calls = 0
    for year in years:
        rows = fetch(133, year)
        calls += 1
        print(f"[registry] {year}: {len(rows)} fund houses")
        for row in rows:
            raw = str(row.get("Anchor Investor", ""))
            m, t = ID_190.search(raw), TITLE.search(raw)
            if not m or not t:
                continue
            hid, hname = m.group(1), " ".join(t.group(1).split()).title()
            n_issues = row.get("No. of Issues") or 0
            h = houses.setdefault(hname, {"id": hid, "deals": {}, "years": {}})
            if h["years"].get(str(year)) == n_issues:
                continue                       # unchanged since last run
            schemes = fetch(190, year, hid)
            calls += 1
            time.sleep(0.25)
            for srow in schemes:
                sraw = str(srow.get("Anchor Investor", ""))
                sm = ID_134.search(sraw)
                if not sm:
                    continue
                deals = fetch(134, year, sm.group(1))
                calls += 1
                time.sleep(0.25)
                for drow in deals:
                    slug = drow.get("~urlrewrite_folder_name")
                    if not slug:
                        continue
                    inv = float(str(drow.get("Amount Invested (Rs.cr.)") or 0).replace(",", "") or 0)
                    shs = str(drow.get("Shares Alloted") or "0").replace(",", "")
                    lg = PCT.search(str(drow.get("Close Price on Listing (Rs.)") or ""))
                    cg = PCT.search(str(drow.get("Market Price (Rs.)") or ""))
                    d = h["deals"].setdefault(slug, {"inv": 0, "sh": 0, "lg": None, "cg": None})
                    d["inv"] = round(d["inv"] + inv, 2)
                    d["sh"] += int(shs) if shs.isdigit() else 0
                    d["lg"] = float(lg.group(1)) if lg else d["lg"]
                    d["cg"] = float(cg.group(1)) if cg else d["cg"]
            h["years"][str(year)] = n_issues
        time.sleep(0.5)
    reg["updated"] = today.isoformat()
    os.makedirs("data", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False)
    n_deals = sum(len(h["deals"]) for h in houses.values())
    print(f"[registry] {len(houses)} houses, {n_deals} deal links, {calls} API calls")


if __name__ == "__main__":
    main()
