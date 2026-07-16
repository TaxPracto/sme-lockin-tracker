#!/usr/bin/env python3
"""
Unlock Radar scraper v2.
Sources (chittorgarh.com):
  1. Report #156 (anchor lock-in end dates) for years Y-2..Y  -> IPO universe + anchor dates + BOA
  2. Per-IPO detail pages (cached in data/ipo_meta.json)      -> pre/post shares, promoter pre/post %
Computes events per SME IPO:
  A30 / A90     anchor tranches (dates as published)
  PRE6M         non-promoter pre-IPO holders unlock, BOA + 6 months (estimated)
  PX1Y / PX2Y   promoter holding above 20% MPC: 50%+50% at 1y/2y for listings
                on/after 2025-03-08 (ICDR amendment), else 100% at 1y (estimated)
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
    "Accept": "application/json,text/html",
}
TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r'href="([^"]+)"')
REGIME_CUTOFF = "2025-03-08"       # ICDR (Amendment) Regulations, 2025 - phased promoter release
META_FETCH_CAP = 250               # per-run cap on new IPO page fetches
META_PATH = "data/ipo_meta.json"


def fetch_year(year: int) -> list:
    fy = f"{year}-{str(year + 1)[-2:]}"
    url = API.format(year=year, fy=fy) + f"?search=&v={dt.datetime.now().strftime('%H-%M')}"
    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            rows = r.json().get("reportTableData") or []
            print(f"[scraper] report156 year {year}: {len(rows)} rows")
            return rows
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch year {year}: {last_err}")


def _int(v):
    if v is None:
        return None
    s = str(v).replace(",", "").strip()
    return int(s) if s.isdigit() else None


def _float(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def _iso(v, fallback_display=None):
    if v:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", str(v))
        if m:
            return m.group(1)
    if fallback_display:
        for fmt in ("%d-%b-%Y", "%b %d, %Y", "%d %b %Y", "%a, %b %d, %Y"):
            try:
                return dt.datetime.strptime(str(fallback_display).strip(), fmt).date().isoformat()
            except ValueError:
                continue
    return None


def add_months(iso_date: str, months: int) -> str:
    d = dt.date.fromisoformat(iso_date)
    y, m = d.year + (d.month - 1 + months) // 12, (d.month - 1 + months) % 12 + 1
    last = [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
            31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return dt.date(y, m, min(d.day, last)).isoformat()


def parse_row(row: dict):
    raw = str(row.get("Company", ""))
    name = TAG_RE.sub("", raw).strip()
    href = HREF_RE.search(raw.replace('\\"', '"'))
    url = href.group(1) if href else None
    slug = None
    if url:
        m = re.search(r"/ipo/([^/]+)/(\d+)/?", url)
        if m:
            slug = m.group(1)
    return {
        "company": name,
        "slug": slug or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
        "url": url,
        "category": str(row.get("Issue Category", "")).strip() or "Unknown",
        "anchor_allotment_date": _iso(None, row.get("Allotment Date")),
        "boa_date": _iso(row.get("~Timetable_BOA_dt")),
        "d30": _iso(row.get("~AnchorDate1"), row.get("30 days lock-in expiry date")),
        "d90": _iso(row.get("~AnchorDate2"), row.get("90 days lock-in expiry date")),
        "anchor_shares": _int(row.get("Total No. of shares allotted to Anchor Investors")),
        "anchor_investment_cr": _float(row.get("Total Investment by Anchor Investors (Rs.cr.)")),
        "pct_of_issue": _float(row.get("% of Issue Amount")),
        "isin": row.get("~isin"),
        "nse_symbol": row.get("~nse_symbol"),
        "bse_code": row.get("~bse_script_code"),
    }


# ---------- per-IPO metadata (pre/post shares, promoter %) ----------
PRE_SH_RE = re.compile(r"Share\s*Holding\s*Pre\s*Issue.{0,700}?(\d{1,3}(?:,\d{2,3}){2,})", re.S | re.I)
POST_SH_RE = re.compile(r"Share\s*Holding\s*Post\s*Issue.{0,700}?(\d{1,3}(?:,\d{2,3}){2,})", re.S | re.I)
PROM_RE = re.compile(r"Promoter\s*Holding[^%]{0,600}?([\d]{1,2}\.\d{1,2})\s*%.{0,300}?([\d]{1,2}\.\d{1,2})\s*%", re.S | re.I)
LIST_DT_RE = re.compile(r"Listing\s*Date.{0,200}?(\w{3},\s*\w{3}\s*\d{1,2},\s*\d{4}|\d{2}-\w{3}-\d{4})", re.S | re.I)
ANCHOR_SEC_RE = re.compile(r"Anchor\s*Investors?\s*(?:List|Detail)?(.{0,12000}?)(?:<h[23]|Anchor\s*lock-in|IPO\s*Reservation|Promoter)", re.S | re.I)
# Lead manager(s): name links use /report/ipo-lead-manager-review/112/<LM_ID>/ — the numeric
# id is Chittorgarh's stable LM identifier (canonical key; sidesteps name-spelling drift).
LM_RE = re.compile(r"ipo-lead-manager-review/112/(\d+)[^>]*>(.*?)</a>", re.S | re.I)
FUND_HINT = re.compile(r"(fund|llp|limited|ltd|trust|mf|aif|capital|ventures?|securities|invest|wealth|advisors|portfolio|opportunit|emerging|india|global|alpha|growth)", re.I)
NAME_CELL_RE = re.compile(r">\s*([A-Z][A-Za-z0-9&().,'\- ]{6,80})\s*<")


def fetch_meta(url: str):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    html = r.text
    meta = {"fetched": dt.date.today().isoformat()}
    m = PRE_SH_RE.search(html)
    meta["pre_shares"] = _int(m.group(1)) if m else None
    m = POST_SH_RE.search(html)
    meta["post_shares"] = _int(m.group(1)) if m else None
    m = PROM_RE.search(html)
    if m:
        pre_pct, post_pct = float(m.group(1)), float(m.group(2))
        if 0 < pre_pct <= 100 and 0 < post_pct <= 100:
            meta["prom_pre_pct"], meta["prom_post_pct"] = pre_pct, post_pct
    m = LIST_DT_RE.search(html)
    meta["listing_date"] = _iso(None, m.group(1).replace("  ", " ")) if m else None
    names = []
    sec = ANCHOR_SEC_RE.search(html)
    if sec:
        seen = set()
        for cand in NAME_CELL_RE.findall(sec.group(1)):
            cand = cand.strip().rstrip(".,")
            low = cand.lower()
            if len(cand) < 7 or not FUND_HINT.search(cand):
                continue
            if any(b in low for b in ("anchor", "lock-in", "shares", "invest amount", "bid date", "investment by",
                                       "click", "chittorgarh", "list of", "allotted", "total")):
                continue
            if low in seen:
                continue
            seen.add(low)
            names.append(cand)
            if len(names) >= 20:
                break
    meta["anchor_names"] = names
    lms, lseen = [], set()
    for _lid, _ltxt in LM_RE.findall(html):
        nm = " ".join(TAG_RE.sub("", _ltxt).replace("&amp;", "&").split()).strip().rstrip(".,")
        if not nm or len(nm) < 3 or _lid in lseen:
            continue
        lseen.add(_lid)
        lms.append([int(_lid), nm])
    meta["lm"] = lms   # ALWAYS set (even []) so cached entries are not refetched forever
    return meta


def build_events(rec: dict, meta: dict, today_iso: str):
    ev = []
    for tr, d in (("A30", rec["d30"]), ("A90", rec["d90"])):
        if d:
            sh = rec["anchor_shares"] // 2 if rec["anchor_shares"] else None
            val = rec["anchor_investment_cr"] / 2 if rec["anchor_investment_cr"] else None
            pct = round(sh / meta["post_shares"] * 100, 2) if sh and meta.get("post_shares") else None
            ev.append({"t": tr, "d": d, "sh": sh, "pct": pct, "val": val, "est": False})
    boa = rec.get("boa_date")
    if not boa or rec["category"] != "SME":
        return ev
    post, pre = meta.get("post_shares"), meta.get("pre_shares")
    pre_pct, post_pct = meta.get("prom_pre_pct"), meta.get("prom_post_pct")
    # PRE-IPO 6M: non-promoter pre-issue holders
    d6 = add_months(boa, 6)
    sh6 = int(pre * (1 - pre_pct / 100)) if pre and pre_pct is not None else None
    p6 = round(sh6 / post * 100, 2) if sh6 and post else None
    if d6 >= "2026-01-01":  # keep file lean: skip long-gone events
        ev.append({"t": "PRE6M", "d": d6, "sh": sh6, "pct": p6, "val": None, "est": True})
    # Promoter excess over 20% MPC
    if post and post_pct is not None and post_pct > 20:
        excess = int(post * (post_pct - 20) / 100)
        listing = meta.get("listing_date") or boa
        phased = listing >= REGIME_CUTOFF
        if phased:
            for months, frac in ((12, 0.5), (24, 0.5)):
                dd = add_months(boa, months)
                if dd >= "2026-01-01":
                    ev.append({"t": "PX1Y" if months == 12 else "PX2Y", "d": dd,
                               "sh": int(excess * frac),
                               "pct": round(excess * frac / post * 100, 2),
                               "val": None, "est": True})
        else:
            dd = add_months(boa, 12)
            if dd >= "2026-01-01":
                ev.append({"t": "PX1Y", "d": dd, "sh": excess,
                           "pct": round(excess / post * 100, 2), "val": None, "est": True})
    return ev


def main():
    today = dt.datetime.now(IST).date()
    years_env = os.environ.get("LOCKIN_YEARS")
    years = ([int(y) for y in years_env.split(",")] if years_env
             else [today.year - 2, today.year - 1, today.year])

    all_rows = []
    for y in years:
        all_rows.extend(fetch_year(y))
        time.sleep(2)

    records, skipped = {}, []
    for row in all_rows:
        rec = parse_row(row)
        if not rec["d30"] and not rec["d90"]:
            skipped.append(rec["company"])
            continue
        records[rec["slug"]] = rec

    # ---- metadata cache ----
    meta_cache = {}
    if os.path.exists(META_PATH):
        with open(META_PATH, encoding="utf-8") as f:
            meta_cache = json.load(f)
    horizon = (today - dt.timedelta(days=800)).isoformat()   # ~26 months back
    fetched = 0
    for slug, rec in records.items():
        if rec["category"] != "SME" or not rec["url"]:
            continue
        if (rec.get("boa_date") or "0000") < horizon:
            continue
        cached = meta_cache.get(slug)
        if cached and cached.get("post_shares") and "anchor_names" in cached and "lm" in cached:
            continue
        if cached and cached.get("_attempts", 0) >= 8:
            continue
        if fetched >= META_FETCH_CAP:
            continue
        try:
            meta = fetch_meta(rec["url"])
            # defensive merge: a refetch (e.g. the one-time lm backfill) must never
            # lose previously-captured fields to a transient page change
            if cached:
                for _k in ("pre_shares", "post_shares", "prom_pre_pct", "prom_post_pct", "listing_date"):
                    if meta.get(_k) is None and cached.get(_k) is not None:
                        meta[_k] = cached[_k]
                if not meta.get("anchor_names") and cached.get("anchor_names"):
                    meta["anchor_names"] = cached["anchor_names"]
            meta["_attempts"] = (cached or {}).get("_attempts", 0) + 1
            meta_cache[slug] = meta
            fetched += 1
            time.sleep(1.2)
        except Exception as e:  # noqa: BLE001
            print(f"[meta] {slug}: {e}")
            meta_cache[slug] = {**(cached or {}), "_attempts": (cached or {}).get("_attempts", 0) + 1}
        if fetched and fetched % 25 == 0:
            print(f"[meta] fetched {fetched} IPO pages...")
    print(f"[meta] new pages this run: {fetched}, cache size: {len(meta_cache)}")

    today_iso = today.isoformat()
    recs = []
    for rec in records.values():
        meta = meta_cache.get(rec["slug"], {})
        rec["pre_shares"] = meta.get("pre_shares")
        rec["post_shares"] = meta.get("post_shares")
        rec["prom_pre_pct"] = meta.get("prom_pre_pct")
        rec["prom_post_pct"] = meta.get("prom_post_pct")
        rec["listing_date"] = meta.get("listing_date")
        rec["anchor_names"] = meta.get("anchor_names") or []
        rec["lm"] = meta.get("lm") or []   # [[lm_id, name], ...] — SME lead manager(s)
        if rec["pre_shares"] and rec["prom_pre_pct"] is not None:
            rec["nonprom_pre_shares"] = int(rec["pre_shares"] * (1 - rec["prom_pre_pct"] / 100))
            rec["nonprom_pre_pct_of_post"] = (round(rec["nonprom_pre_shares"] / rec["post_shares"] * 100, 2)
                                              if rec["post_shares"] else None)
        else:
            rec["nonprom_pre_shares"] = None
            rec["nonprom_pre_pct_of_post"] = None
        rec["events"] = build_events(rec, meta, today_iso)
        recs.append(rec)

    recs.sort(key=lambda r: r["d30"] or "9999", reverse=True)
    if len(recs) < 5:
        raise RuntimeError(f"Only {len(recs)} records parsed - API may have changed. Failing loudly.")

    os.makedirs("data", exist_ok=True)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta_cache, f, ensure_ascii=False)
    out = {
        "generated_at": dt.datetime.now(IST).isoformat(timespec="seconds"),
        "source": "chittorgarh.com report #156 + IPO pages",
        "years": years,
        "records": recs,
    }
    with open("data/lockins.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    n_ev = sum(len(r["events"]) for r in recs)
    n_lm = sum(1 for r in recs if r["category"] == "SME" and r.get("lm"))
    print(f"[scraper] {len(recs)} records, {n_ev} events "
          f"({sum(1 for r in recs if r['category']=='SME')} SME, lead manager known for {n_lm}), "
          f"skipped {len(skipped)}")


if __name__ == "__main__":
    sys.exit(main())
