#!/usr/bin/env python3
"""
Outcome memory: records what price did after each unlock event.
For every past event, once prices exist for the last session before the event
and ~5 sessions after, stores {pre_close, post5_close, ret5_pct}.
Output: data/outcomes.json  {"<slug>|<type>": {...}}
Runs daily after price_feed.py. No external calls; pure bookkeeping.
"""
import datetime as dt
import json
import os

def load(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def main():
    data = load("data/lockins.json", {"records": []})
    hist = load("data/prices.json", {}).get("hist", {})
    out = load("data/outcomes.json", {})
    today = dt.date.today().isoformat()
    added = 0
    for r in data["records"]:
        isin = str(r.get("isin") or "").strip()
        h = hist.get(isin)
        if not h:
            continue
        dates = [e[0] for e in h]
        closes = {e[0]: e[1] for e in h}
        for e in r.get("events", []):
            d = e.get("d")
            if not d or d >= today:
                continue
            key = f"{r['slug']}|{e['t']}"
            if key in out and out[key].get("ret5_pct") is not None:
                continue
            pre_dates = [x for x in dates if x < d]
            post_dates = [x for x in dates if x >= d]
            if not pre_dates or len(post_dates) < 5:
                continue
            pre = closes[pre_dates[-1]]
            post5 = closes[post_dates[4]]
            if not pre:
                continue
            out[key] = {
                "slug": r["slug"], "type": e["t"], "date": d,
                "pct_cap": e.get("pct"), "dov": (round(e["sh"] / r["avg_vol"], 1)
                                                 if e.get("sh") and r.get("avg_vol") else None),
                "pre_close": pre, "post5_close": post5,
                "ret5_pct": round((post5 - pre) / pre * 100, 2),
            }
            added += 1
    with open("data/outcomes.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    done = sum(1 for v in out.values() if v.get("ret5_pct") is not None)
    print(f"[outcomes] recorded {added} new, total complete: {done}")

if __name__ == "__main__":
    main()
