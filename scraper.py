#!/usr/bin/env python3
"""
Anchor Lock-in Tracker - scraper
Pulls anchor investor lock-in expiry dates for Indian IPOs (SME + Mainboard)
from Chittorgarh's report JSON API and writes data/lockins.json.

Runs daily via GitHub Actions. No credentials needed.
"""
import json
import os
import re
import sys
import time
import datetime as dt
from zoneinfo import ZoneInfo

import requests

IST = ZoneInfo("Asia/Kolkata")
API = "https://webnodejs.chittorgarh.com/cloud/report/data-read/156/1/2/{year}/{fy}/0/all/0"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Referer": "https://www.chittorgarh.com/report/anchor-investor-lock-in-end-dates/156/sme/",
    "Accept": "application/json",
}
TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r'href="([^"]+)"')


def fetch_year(year: int) -> list:
    fy = f"{year}-{str(year + 1)[-2:]}"
    url = API.format(year=year, fy=fy) + f"?search=&v={dt.datetime.now().strftime('%H-%M')}"
    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            rows = data.get("reportTableData") or []
            print(f"[scraper] year {year}: {len(rows)} rows")
            return rows
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait = 5 * (attempt + 1)
            print(f"[scraper] year {year} attempt {attempt + 1} failed: {e}; retrying in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Failed to fetch year {year}: {last_err}")


def _clean_int(v):
    if v is None:
        return None
    s = str(v).replace(",", "").strip()
    return int(s) if s.isdigit() else None


def _clean_float(v):
    if v is None:
        return None
    s = str(v).replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _iso_date(v, fallback_display=None):
    """Prefer machine field '2026-08-13T00:00:00.000Z'; fallback '13-Aug-2026'."""
    if v:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", str(v))
        if m:
            return m.group(1)
    if fallback_display:
        for fmt in ("%d-%b-%Y", "%b %d, %Y", "%d %b %Y"):
            try:
                return dt.datetime.strptime(str(fallback_display).strip(), fmt).date().isoformat()
            except ValueError:
                continue
    return None


def parse_row(row: dict):
    raw_company = str(row.get("Company", ""))
    name = TAG_RE.sub("", raw_company).strip()
    href_m = HREF_RE.search(raw_company.replace('\\"', '"'))
    url = href_m.group(1) if href_m else None
    slug = None
    if url:
        m = re.search(r"/ipo/([^/]+)/(\d+)/?", url)
        if m:
            slug = m.group(1)
    d30 = _iso_date(row.get("~AnchorDate1"), row.get("30 days lock-in expiry date"))
    d90 = _iso_date(row.get("~AnchorDate2"), row.get("90 days lock-in expiry date"))
    rec = {
        "company": name,
        "slug": slug or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
        "url": url,
        "category": str(row.get("Issue Category", "")).strip() or "Unknown",
        "anchor_allotment_date": _iso_date(None, row.get("Allotment Date")),
        "boa_date": _iso_date(row.get("~Timetable_BOA_dt"), None),
        "d30": d30,
        "d90": d90,
        "anchor_shares": _clean_int(row.get("Total No. of shares allotted to Anchor Investors")),
        "anchor_investment_cr": _clean_float(row.get("Total Investment by Anchor Investors (Rs.cr.)")),
        "pct_of_issue": _clean_float(row.get("% of Issue Amount")),
        "isin": row.get("~isin"),
        "nse_symbol": row.get("~nse_symbol"),
        "bse_code": row.get("~bse_script_code"),
    }
    return rec


def main():
    today = dt.datetime.now(IST).date()
    years_env = os.environ.get("LOCKIN_YEARS")
    years = [int(y) for y in years_env.split(",")] if years_env else [today.year - 1, today.year]

    all_rows = []
    for y in years:
        all_rows.extend(fetch_year(y))
        time.sleep(2)  # be polite

    records, skipped = {}, []
    for row in all_rows:
        rec = parse_row(row)
        if not rec["d30"] and not rec["d90"]:
            skipped.append(rec["company"])
            continue
        records[rec["slug"]] = rec  # dedupe across years

    recs = sorted(records.values(), key=lambda r: r["d30"] or "9999", reverse=True)
    if len(recs) < 5:
        raise RuntimeError(f"Only {len(recs)} records parsed - API may have changed. Failing loudly.")

    out = {
        "generated_at": dt.datetime.now(IST).isoformat(timespec="seconds"),
        "source": "chittorgarh.com report #156 (anchor lock-in end dates)",
        "years": years,
        "records": recs,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/lockins.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"[scraper] wrote data/lockins.json: {len(recs)} records "
          f"({sum(1 for r in recs if r['category']=='SME')} SME), skipped {len(skipped)}: {skipped[:5]}")


if __name__ == "__main__":
    sys.exit(main())
