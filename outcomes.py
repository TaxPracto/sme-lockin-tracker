#!/usr/bin/env python3
"""
Outcome memory v2 (backtest-capable).
Uses data/history.json (full backfill) when present, else data/prices.json (rolling).
For every past unlock event computes:
  runup20  price move T-20 -> T-1 (momentum into the unlock)
  ret1/ret5/ret20  close-to-close move after the event
  dov_ev   unlocking shares vs avg volume of the 20 sessions BEFORE the event
  pl_at_unlock  holders' gain% vs IPO issue price on the eve of the unlock
Writes data/outcomes.json. Pure bookkeeping, no network.
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


def get_series():
    h = load("data/history.json", None)
    if h and h.get("series"):
        return {isin: sorted(d.items()) for isin, d in h["series"].items()}
    ph = load("data/prices.json", {}).get("hist", {})
    return {isin: [(e[0], [e[1], e[2] if len(e) > 2 else 0]) for e in rows] for isin, rows in ph.items()}


def main():
    data = load("data/lockins.json", {"records": []})
    series = get_series()
    out = load("data/outcomes.json", {})
    today = dt.date.today().isoformat()
    added = 0
    for r in data["records"]:
        isin = str(r.get("isin") or "").strip()
        s = series.get(isin)
        if not s:
            continue
        dates = [x[0] for x in s]
        closes = [x[1][0] for x in s]
        vols = [x[1][1] for x in s]
        inv, ash = r.get("anchor_investment_cr"), r.get("anchor_shares")
        issue_px = (inv * 1e7 / ash) if inv and ash else None
        for e in r.get("events", []):
            d = e.get("d")
            if not d or d >= today:
                continue
            key = f"{r['slug']}|{e['t']}"
            if key in out and out[key].get("ret5") is not None:
                continue
            pre_idx = [i for i, x in enumerate(dates) if x < d]
            post_idx = [i for i, x in enumerate(dates) if x >= d]
            if not pre_idx or len(post_idx) < 5:
                continue
            p = pre_idx[-1]
            pre = closes[p]
            if not pre:
                continue
            def ret(n):
                return (round((closes[post_idx[n - 1]] - pre) / pre * 100, 2)
                        if len(post_idx) >= n else None)
            vwin = [v for v in vols[max(0, p - 19):p + 1] if v]
            avg_vol = sum(vwin) / len(vwin) if vwin else None
            r20 = (round((pre - closes[max(0, p - 20)]) / closes[max(0, p - 20)] * 100, 1)
                   if p >= 1 and closes[max(0, p - 20)] else None)
            out[key] = {
                "slug": r["slug"], "type": e["t"], "date": d,
                "pct_cap": e.get("pct"),
                "dov_ev": round(e["sh"] / avg_vol, 1) if e.get("sh") and avg_vol else None,
                "runup20": r20,
                "pl_at_unlock": round((pre - issue_px) / issue_px * 100, 1) if issue_px else None,
                "pre_close": pre, "ret1": ret(1), "ret5": ret(5), "ret20": ret(20),
            }
            added += 1
    with open("data/outcomes.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    done = sum(1 for v in out.values() if v.get("ret5") is not None)
    print(f"[outcomes] +{added} new, total complete: {done}")


if __name__ == "__main__":
    main()
