#!/usr/bin/env python3
"""Builds docs/index.html + docs/lockins.ics + docs/data.json from data/lockins.json (v2: multi-event)."""
import datetime as dt
import json
import os

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

with open("data/lockins.json", encoding="utf-8") as f:
    payload = json.load(f)

records = payload["records"]

# merge daily price/volume feed (optional, graceful if absent)
_prices = {}
try:
    with open("data/prices.json", encoding="utf-8") as _f:
        _prices = json.load(_f).get("hist", {})
except Exception:
    _prices = {}
for _r in records:
    _h = _prices.get(str(_r.get("isin") or "").strip())
    if _h:
        _r["last_close"], _r["close_date"] = _h[-1][1], _h[-1][0]
        _vols = [_e[2] for _e in _h if len(_e) > 2 and _e[2]]
        _r["avg_vol"] = int(sum(_vols) / len(_vols)) if _vols else None
    else:
        _r["last_close"] = _r["close_date"] = _r["avg_vol"] = None
    _inv, _sh = _r.get("anchor_investment_cr"), _r.get("anchor_shares")
    _r["issue_px"] = round(_inv * 1e7 / _sh, 2) if _inv and _sh else None
    _r["chg_from_issue_pct"] = (round((_r["last_close"] - _r["issue_px"]) / _r["issue_px"] * 100, 1)
                                if _r.get("last_close") and _r.get("issue_px") else None)
now_ist = dt.datetime.now(IST)
gen_label = now_ist.strftime("%d %b %Y, %H:%M IST")
today_iso = now_ist.date().isoformat()

TYPE_NAME = {"A30": "30D anchor", "A90": "90D anchor", "PRE6M": "6M pre-IPO",
             "PX1Y": "1Y promoter", "PX2Y": "2Y promoter"}

# ---------------- ICS ----------------
def esc(s):
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;")

lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//UnlockRadar//v2//EN",
         "CALSCALE:GREGORIAN", "X-WR-CALNAME:Unlock Radar - lock-in expiries",
         "X-WR-TIMEZONE:Asia/Kolkata"]
for r in records:
    for e in r.get("events", []):
        if not e["d"] or e["d"] < today_iso:
            continue
        bits = []
        if e.get("sh"):
            bits.append(f"{e['sh']:,} sh")
        if e.get("pct"):
            bits.append(f"{e['pct']}% of capital")
        if e.get("val"):
            bits.append(f"~Rs.{e['val']:.1f} cr")
        summ = f"🔓 {r['company']} — {TYPE_NAME[e['t']]} unlock" + (f" ({'; '.join(bits)})" if bits else "")
        dstart = e["d"].replace("-", "")
        dend = (dt.date.fromisoformat(e["d"]) + dt.timedelta(days=1)).isoformat().replace("-", "")
        lines += ["BEGIN:VEVENT", f"UID:{r['slug']}-{e['t']}@unlockradar",
                  f"DTSTART;VALUE=DATE:{dstart}", f"DTEND;VALUE=DATE:{dend}",
                  f"SUMMARY:{esc(summ)}",
                  f"DESCRIPTION:{esc(('Estimated from SEBI ICDR rules. ' if e.get('est') else '') + (r['url'] or ''))}",
                  "END:VEVENT"]
lines.append("END:VCALENDAR")
os.makedirs("docs", exist_ok=True)
with open("docs/lockins.ics", "w", encoding="utf-8") as f:
    f.write("\r\n".join(lines) + "\r\n")
with open("docs/data.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=1)
open("docs/.nojekyll", "w").close()

# ---------------- HTML ----------------

# outcome history stats (by event type) + anchor fund registry
_outs = {}
try:
    with open("data/outcomes.json", encoding="utf-8") as _f:
        _outs = json.load(_f)
except Exception:
    _outs = {}
def _r5(_o):
    return _o.get("ret5", _o.get("ret5_pct"))

def _med(_v):
    _v = sorted(_v)
    return round(_v[len(_v)//2], 1) if _v else None

def _sgn(_v):
    return None if _v is None else f"{'+' if _v >= 0 else ''}{_v}%"

_by_type = {}
for _o in _outs.values():
    if _r5(_o) is not None:
        _by_type.setdefault(_o["type"], []).append(_r5(_o))
OUTCOME_STATS = {_t: {"n": len(_v), "med": _med(_v)} for _t, _v in _by_type.items()}
OUT_KEYED = {}
for _k, _o in _outs.items():
    if _r5(_o) is not None:
        OUT_KEYED[_k] = {"r1": _o.get("ret1"), "r5": _r5(_o), "r20": _o.get("ret20"),
                         "pre": _o.get("pre_close"), "dov": _o.get("dov_ev"), "pl": _o.get("pl_at_unlock")}
_odates = sorted(o["date"] for o in _outs.values() if _r5(o) is not None and o.get("date"))
def _dmy(_s):
    _M = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{_s[8:10]} {_M[int(_s[5:7])]} {_s[:4]}"
_WINDOW = f"{_dmy(_odates[0])} to {_dmy(_odates[-1])}" if _odates else "syncing"

# ---------------- backtest report (docs/backtest.html) ----------------
def _bucket_rows(keyfn, buckets, only_anchor=False):
    rows = []
    for lbl, lo, hi in buckets:
        vals = [_r5(o) for o in _outs.values()
                if _r5(o) is not None and (not only_anchor or o["type"] in ("A30", "A90"))
                and keyfn(o) is not None and lo <= keyfn(o) < hi]
        neg = sum(1 for v in vals if v < 0)
        rows.append((lbl, len(vals), _sgn(_med(vals)), f"{round(neg / len(vals) * 100)}%" if vals else None))
    return rows

_registry = {}
try:
    with open("data/registry.json", encoding="utf-8") as _f:
        _registry = json.load(_f).get("houses", {})
except Exception:
    _registry = {}
_slug_names = {}
_deal_counts = {}
_house_lg = {}
for _hn, _h in _registry.items():
    _deal_counts[_hn] = len(_h.get("deals", {}))
    _lgs = [d.get("lg") for d in _h.get("deals", {}).values() if d.get("lg") is not None]
    _cgs = [d.get("cg") for d in _h.get("deals", {}).values() if d.get("cg") is not None]
    _house_lg[_hn] = (round(sum(_lgs)/len(_lgs), 1) if _lgs else None,
                      round(sum(_cgs)/len(_cgs), 1) if _cgs else None)
    for _slug in _h.get("deals", {}):
        _slug_names.setdefault(_slug, []).append(_hn)
if not _registry:                      # fallback to page-scraped names until registry syncs
    for _r0 in records:
        if _r0.get("category") == "SME":
            _slug_names[_r0["slug"]] = [" ".join(n.split()).title() for n in (_r0.get("anchor_names") or [])
                                        if "investment by" not in n.lower()]
    for _names in _slug_names.values():
        for _nm in _names:
            _deal_counts[_nm] = _deal_counts.get(_nm, 0) + 1
_fund_obs = {}
for _o in _outs.values():
    if _o["type"] not in ("A30", "A90") or _r5(_o) is None:
        continue
    for _nm in _slug_names.get(_o["slug"], []):
        _fund_obs.setdefault(" ".join(_nm.split()).title(), []).append(_o)

def _avg(_v):
    _v = [x for x in _v if x is not None]
    return round(sum(_v) / len(_v), 1) if _v else None

FUND_TABLE = []
for _k, _obs in _fund_obs.items():
    _rets = [_r5(_o) for _o in _obs]
    _n = len(_rets)
    if _n < 3:
        continue
    _medt5 = _med(_rets)
    _pneg = round(sum(1 for x in _rets if x < 0) / _n * 100)
    _apl = _avg([_o.get("pl_at_unlock") for _o in _obs])
    _adov = _avg([_o.get("dov_ev") for _o in _obs])
    _aru = _avg([_o.get("runup20") for _o in _obs])
    _score = 50 + 2.5 * max(min(_medt5, 10), -10) - 0.3 * (_pneg - 50) \
             - (1.2 * max((_adov or 0) - 3, 0)) - 0.05 * max((_aru or 0) - 25, 0) \
             + min(_deal_counts.get(_k, _n), 10) * 0.5
    _grade = "STICKY" if _score >= 60 else ("NEUTRAL" if _score >= 45 else "FLIPPER")
    _lg, _cg = _house_lg.get(_k, (None, None)) if "_house_lg" in dir() else (None, None)
    FUND_TABLE.append({"fund": _k, "deals": _deal_counts.get(_k, _n), "n": _n, "med": _medt5,
                       "pneg": _pneg, "apl": _apl, "adov": _adov, "aru": _aru, "lg": _lg, "cg": _cg,
                       "score": round(_score, 1), "grade": _grade})
FUND_TABLE.sort(key=lambda x: -x["score"])
FUND_ROWS = [(f["fund"], f["n"], f["med"], f["pneg"]) for f in sorted(FUND_TABLE, key=lambda x: x["med"] if x["med"] is not None else 999)][:15]
_UNGRADED = sorted([(k, c) for k, c in _deal_counts.items() if c >= 1 and k not in {f["fund"] for f in FUND_TABLE}],
                   key=lambda x: (-x[1], x[0]))

NAV = """<div class="nav"><a href="index.html" class="{a}">Radar</a><a href="anchors.html" class="{b}">Anchor ranks</a><a href="backtest.html" class="{c}">Backtest</a></div>"""
_NAVCSS = ".nav{display:flex;gap:8px;margin:0 0 18px}.nav a{padding:7px 16px;border:1px solid rgba(24,33,51,.16);border-radius:99px;font-size:12px;font-weight:600;color:#3F4756;background:#fff;text-decoration:none}.nav a.on{background:#1A2130;color:#fff;border-color:#1A2130}"

_gcol = {"STICKY": ("#E1F5EE", "#0F6E56"), "NEUTRAL": ("#FBF0DA", "#854F0B"), "FLIPPER": ("#FBE4E7", "#A32D2D")}

# ---- score replay: per-unlock points + 90-day momentum (anchors overlay + trend column) ----
_slug_co = {}
for _r0 in records:
    if _r0.get("slug"):
        _slug_co[_r0["slug"]] = _r0.get("company") or _r0["slug"]
def _slug_pretty(_s):
    return _slug_co.get(_s) or " ".join(_s.replace("-", " ").split()).title()
_MON = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
def _dshort(_s):
    return f"{_s[8:10]} {_MON[int(_s[5:7])]} {_s[2:4]}" if _s and len(_s) >= 10 else ""
_reg_tc = {}
for _hn0, _h0 in _registry.items():
    _reg_tc[" ".join(_hn0.split()).title()] = _h0.get("deals", {})
_MOM_CUT = (now_ist.date() - dt.timedelta(days=90)).isoformat()

def _replay(_k, _obs):
    """Rebuild the fund score after each measured unlock, oldest first.
    Experience bonus held constant at today's value so the last point equals the table score.
    Returns (events, momentum_over_90d, is_new)."""
    _seq = sorted(_obs, key=lambda o: (o.get("date") or "", o["slug"], o["type"]))
    _bonus = min(_deal_counts.get(_k, len(_obs)), 10) * 0.5
    _evs, _scs = [], []
    _rets2, _dovs2, _rus2 = [], [], []
    for _o in _seq:
        _rets2.append(_r5(_o))
        if _o.get("dov_ev") is not None:
            _dovs2.append(_o["dov_ev"])
        if _o.get("runup20") is not None:
            _rus2.append(_o["runup20"])
        _m2 = _med(_rets2)
        _pn2 = round(sum(1 for x in _rets2 if x < 0) / len(_rets2) * 100)
        _ad2 = round(sum(_dovs2) / len(_dovs2), 1) if _dovs2 else None
        _ar2 = round(sum(_rus2) / len(_rus2), 1) if _rus2 else None
        _sc2 = 50 + 2.5 * max(min(_m2, 10), -10) - 0.3 * (_pn2 - 50) \
               - (1.2 * max((_ad2 or 0) - 3, 0)) - 0.05 * max((_ar2 or 0) - 25, 0) + _bonus
        _scs.append(round(_sc2, 1))
        _evs.append({"d": _dshort(_o.get("date") or ""), "co": _slug_pretty(_o["slug"]),
                     "t": "30D" if _o["type"] == "A30" else "90D", "r5": _r5(_o),
                     "sc": _scs[-1], "dl": round(_scs[-1] - _scs[-2], 1) if len(_scs) > 1 else None})
    _pri = [sc for sc, o in zip(_scs, _seq) if (o.get("date") or "") <= _MOM_CUT]
    if not _pri:
        return _evs, None, True
    return _evs, round(_scs[-1] - _pri[-1], 1), False

def _pointers(_f, _mom, _nw, _recent, _pend):
    """2-3 plain-English lines on how this fund is doing. Rebuilt every run, so they
    change automatically as new unlocks get measured."""
    _p = []
    _msgn = f"{'+' if _f['med'] >= 0 else ''}{_f['med']}%"
    if _f["grade"] == "STICKY":
        _p.append(f"Stocks it anchors usually hold up after its unlocks — typical move {_msgn} in the week after.")
    elif _f["grade"] == "FLIPPER":
        _p.append(f"Stocks it anchors usually drop after its unlocks — typical move {_msgn} in the week after.")
    else:
        _p.append(f"About average after its unlocks — typical move {_msgn} in the week after.")
    if _nw:
        _p.append("Too new to show a direction — its whole record is inside the last 90 days.")
    elif _mom is not None and _mom >= 2:
        _p.append(f"Improving: recent unlocks lifted its score by {_mom} points in the last 90 days.")
    elif _mom is not None and _mom <= -2:
        _p.append(f"Slipping: recent unlocks cost it {abs(_mom)} points in the last 90 days.")
    elif _recent:
        _p.append("Holding steady — its recent unlocks barely moved its score.")
    else:
        _p.append("Quiet lately — no unlocks measured in the last 90 days.")
    if _f["adov"] is not None and _f["adov"] > 5:
        _p.append(f"Caution: its unlocks are heavy — {_f['adov']}× a normal day's trading on average.")
    elif _f["aru"] is not None and _f["aru"] > 25:
        _p.append(f"Prices typically climbed {_f['aru']}% into its unlock dates — watch for run-up games.")
    elif _f["pneg"] >= 60:
        _p.append(f"{_f['pneg']} out of 100 of its unlocks saw the stock lower a week later — careful holding through its dates.")
    elif _f["pneg"] <= 35 and _f["n"] >= 10:
        _p.append(f"Reliable so far: only {_f['pneg']} out of 100 of its unlocks saw the stock lower a week later.")
    elif _f["n"] < 10:
        _p.append(f"Small sample: only {_f['n']} unlocks watched so far — hold this read loosely.")
    elif _pend:
        _p.append(f"{len(_pend)} anchored IPOs still have unlocks coming — this read can move soon.")
    return _p[:3]

_FDATA = []
for _f in FUND_TABLE:
    _evs, _mom, _isnew = _replay(_f["fund"], _fund_obs.get(_f["fund"], []))
    _f["mom"], _f["nw"] = _mom, _isnew
    _dl_map = _reg_tc.get(_f["fund"], {})
    _seen = {_o2["slug"] for _o2 in _fund_obs.get(_f["fund"], [])}
    _pend = sorted({_slug_pretty(_s2) for _s2 in _dl_map if _s2 not in _seen})
    _recent = any((_o3.get("date") or "") > _MOM_CUT for _o3 in _fund_obs.get(_f["fund"], []))
    _FDATA.append({
        "fund": _f["fund"], "n": _f["n"], "deals": _f["deals"], "score": _f["score"], "grade": _f["grade"],
        "med": _f["med"], "pneg": _f["pneg"], "adov": _f["adov"], "aru": _f["aru"],
        "cmed": round(2.5 * max(min(_f["med"], 10), -10), 1),
        "cneg": round(-0.3 * (_f["pneg"] - 50), 1),
        "cdov": round(-1.2 * max((_f["adov"] or 0) - 3, 0), 1),
        "cru": round(-0.05 * max((_f["aru"] or 0) - 25, 0), 1),
        "cdl": round(min(_f["deals"], 10) * 0.5, 1),
        "ev": _evs, "mom": _mom, "nw": _isnew, "pend": _pend,
        "pts": _pointers(_f, _mom, _isnew, _recent, _pend)})
_frows = ""
for _i, _f in enumerate(FUND_TABLE):
    _bg, _fg = _gcol[_f["grade"]]
    if _f.get("nw"):
        _tcell = "<span style='color:#727B8A;font-size:11px'>new</span>"
    elif _f.get("mom") is None:
        _tcell = "\u2014"
    elif abs(_f["mom"]) < 0.05:
        _tcell = "0.0"
    else:
        _tc, _aw = ("#0B8A4D", "\u25b2") if _f["mom"] > 0 else ("#E24B4A", "\u25bc")
        _tcell = f"<span style='color:{_tc};font-weight:600'>{'+' if _f['mom'] > 0 else ''}{_f['mom']} {_aw}</span>"
    _frows += (f"<tr><td>{_i+1}</td><td class=\"fname\" data-fi=\"{_i}\" style=\"font-family:'Instrument Sans',sans-serif;font-weight:500\">{_f['fund']}</td>"
               f"<td>{_f['deals']}</td><td>{_f['n']}</td><td>{_f['med']}%</td><td>{_f['pneg']}%</td>"
               f"<td>{_f['lg'] if _f.get('lg') is not None else '—'}%</td><td>{_f['cg'] if _f.get('cg') is not None else '—'}%</td>"
               f"<td>{_f['adov'] if _f['adov'] is not None else '—'}×</td>"
               f"<td><span style='background:{_bg};color:{_fg};padding:2px 10px;border-radius:99px;font-size:10.5px;font-weight:700'>{_f['grade']}</span></td>"
               f"<td>{_tcell}</td></tr>")
_urows = " · ".join(f"{k} ({c})" for k, c in _UNGRADED) or "—"

_mup = sorted([(_i2, _f2) for _i2, _f2 in enumerate(FUND_TABLE) if not _f2.get("nw") and (_f2.get("mom") or 0) >= 0.5],
              key=lambda x: -x[1]["mom"])[:5]
_mdn = sorted([(_i2, _f2) for _i2, _f2 in enumerate(FUND_TABLE) if not _f2.get("nw") and (_f2.get("mom") or 0) <= -0.5],
              key=lambda x: x[1]["mom"])[:5]
def _mrows(_lst, _up):
    _c, _a = ("#0B8A4D", "▲") if _up else ("#E24B4A", "▼")
    _out = ""
    for _i2, _f2 in _lst:
        _out += (f"<div class='mrow' data-fi='{_i2}'><span class='mn'>{_f2['fund']}</span>"
                 f"<span class='mv' style='color:{_c}'>{'+' if _up else ''}{_f2['mom']} {_a}</span></div>")
    return _out or "<div style='font-size:11.5px;color:#727B8A;padding:4px 0'>no clear movers in the last 90 days</div>"
_MOVERS = ("<div class='movers'>"
           "<div class='mcard'><div class='mh'>On the way up · last 90 days</div>" + _mrows(_mup, True) + "</div>"
           "<div class='mcard'><div class='mh'>Slipping · last 90 days</div>" + _mrows(_mdn, False) + "</div></div>")

_ANCH_JS = """<style>
.fname{cursor:pointer;text-decoration:underline dotted rgba(24,33,51,.35);text-underline-offset:3px}
.fname:hover{color:#B36F00}
#fback{position:fixed;inset:0;background:rgba(16,24,40,.45);display:none;align-items:center;justify-content:center;z-index:60;padding:18px}
#fback.on{display:flex}
#fcard{background:#fff;border:1px solid rgba(24,33,51,.16);border-radius:16px;max-width:600px;width:100%;max-height:88vh;overflow-y:auto;padding:24px 26px 20px;box-shadow:0 24px 60px rgba(16,24,40,.25)}
#fcard h3{font-family:Fraunces,serif;font-weight:500;font-size:22px;margin:0 0 2px}
.fsub{font-size:12px;color:#727B8A;margin-bottom:14px}
.srow{display:grid;grid-template-columns:1fr 92px 64px;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid rgba(24,33,51,.08);font-size:12.5px;color:#3F4756}
.srow .in{font-family:'IBM Plex Mono',monospace;font-size:12px;text-align:right;color:#1A2130}
.srow .pt{font-family:'IBM Plex Mono',monospace;font-size:12.5px;font-weight:600;text-align:right}
.srow small{display:block;color:#727B8A;font-size:10.5px;margin-top:1px}
.sbar{height:5px;border-radius:4px;margin-top:5px}
.stot{display:flex;justify-content:space-between;align-items:center;padding:13px 0 4px;font-size:13.5px;font-weight:600}
.fnote{font-size:11px;color:#727B8A;line-height:1.7;margin-top:12px;border-top:1px solid rgba(24,33,51,.12);padding-top:10px}
.ftabs{display:flex;gap:7px;margin:12px 0 12px}
.ftabbtn{border:1px solid rgba(24,33,51,.2);background:#fff;border-radius:99px;padding:5px 14px;font-size:11px;font-weight:600;color:#727B8A;cursor:pointer;font-family:'Instrument Sans',sans-serif}
.ftabbtn.on{background:#1A2130;color:#fff;border-color:#1A2130}
.movers{display:grid;grid-template-columns:1fr 1fr;gap:13px;margin:0 0 14px}
.mcard{background:#fff;border:1px solid rgba(24,33,51,.16);border-radius:12px;padding:12px 16px}
.mh{font-size:10px;letter-spacing:.12em;font-weight:700;color:#727B8A;margin-bottom:5px;text-transform:uppercase}
.mrow{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid rgba(24,33,51,.06);font-size:12.5px;cursor:pointer}
.mrow:last-child{border-bottom:0}
.mrow .mn{text-decoration:underline dotted rgba(24,33,51,.35);text-underline-offset:3px}
.mrow:hover .mn{color:#B36F00}
.mrow .mv{font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:12px}
.hrow{display:grid;grid-template-columns:64px minmax(0,1fr) 64px 46px 50px;gap:8px;align-items:center;padding:7px 0;border-bottom:1px solid rgba(24,33,51,.08);font-size:12.5px;color:#3F4756}
.hrow.hhead{font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:#727B8A;padding:10px 0 4px;border-bottom:1px solid rgba(24,33,51,.16)}
.hd{font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:#727B8A}
.hco{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.ht{font-size:9px;font-weight:700;color:#727B8A;background:#F1EEE6;border-radius:6px;padding:1px 6px;margin-left:5px}
.hr,.hs{font-family:'IBM Plex Mono',monospace;font-size:11.5px;text-align:right}
.dl{font-family:'IBM Plex Mono',monospace;font-size:11.5px;font-weight:700;text-align:right}
@media(max-width:720px){.movers{grid-template-columns:1fr}}
.fpts{background:#F7F5F0;border:1px solid rgba(24,33,51,.12);border-radius:10px;padding:9px 14px;margin:12px 0 0}
.fpt{font-size:12.5px;color:#3F4756;line-height:1.65;padding:2.5px 0;display:flex;gap:9px;align-items:baseline}
.fpt::before{content:'●';font-size:6.5px;color:#B36F00;flex:none;position:relative;top:-2px}
</style>
<div id="fback"><div id="fcard"></div></div>
<script>
(function(){
const tab=document.getElementById('ftab');
const heads=[...tab.rows[0].cells];
const q=document.getElementById('fq');
const pills=[...document.querySelectorAll('.vpill')];
const chk=document.getElementById('fmin');
let vsel='ALL';
const rows=()=>[...tab.rows].slice(1);
function apply(){
  const s=q.value.trim().toLowerCase();
  rows().forEach(r=>{
    const name=r.cells[1].textContent.toLowerCase();
    const verd=r.cells[9].textContent.trim();
    const watched=parseFloat(r.cells[3].textContent)||0;
    const ok=(!s||name.includes(s))&&(vsel==='ALL'||verd===vsel)&&(!chk.checked||watched>=10);
    r.style.display=ok?'':'none';
  });
}
q.addEventListener('input',apply);
chk.addEventListener('change',apply);
pills.forEach(p=>p.addEventListener('click',()=>{vsel=p.dataset.v;pills.forEach(x=>x.classList.toggle('on',x===p));apply();}));
let sc=-1,sd=-1;
function val(r,i){
  const t=r.cells[i].textContent.trim();
  if(t===''||t==='\u2014'||t==='new')return null;
  const n=parseFloat(t.replace(/[+%\u00d7,]/g,''));
  return isNaN(n)?t.toLowerCase():n;
}
heads.forEach((h,i)=>{if(i===0)return;h.addEventListener('click',()=>{
  sd=(sc===i)?-sd:(i===1?1:-1);sc=i;
  heads.forEach(x=>x.classList.remove('sa','sd'));
  h.classList.add(sd===1?'sa':'sd');
  const rs=rows();
  rs.sort((a,b)=>{
    const va=val(a,i),vb=val(b,i);
    if(va===null&&vb===null)return 0;if(va===null)return 1;if(vb===null)return -1;
    if(typeof va==='string'||typeof vb==='string')return String(va).localeCompare(String(vb))*sd;
    return (va-vb)*sd;
  });
  rs.forEach(r=>tab.tBodies[0].appendChild(r));
});});
const FDATA = __FD__;
const gcol = {STICKY:['#E1F5EE','#0F6E56'], NEUTRAL:['#FBF0DA','#854F0B'], FLIPPER:['#FBE4E7','#A32D2D']};
function srow(label, note, input, pts, max){
  const c = pts >= 0 ? '#0B8A4D' : '#E24B4A';
  const w = Math.min(Math.abs(pts) / max * 100, 100);
  return `<div class="srow"><div>${label}<small>${note}</small><div class="sbar" style="background:${c};width:${Math.max(w,1.5)}%;opacity:${pts===0?0.15:1}"></div></div>
    <div class="in">${input}</div><div class="pt" style="color:${c}">${pts >= 0 ? '+' : ''}${pts}</div></div>`;
}
function scoreBody(f){
  return `
    <div class="srow" style="border-bottom:1px dashed rgba(24,33,51,.2)"><div><b>Every fund starts at</b></div><div class="in"></div><div class="pt">50</div></div>
    ${srow('Typical move in the week after its unlocks', 'the big one · 2.5 pts per %, capped at ±10%', (f.med >= 0 ? '+' : '') + f.med + '%', f.cmed, 25)}
    ${srow('How often its stocks fell', 'vs a 50/50 coin-flip · 0.3 pts per % better or worse', f.pneg + '%', f.cneg, 15)}
    ${srow('Heaviness of its unlocks', 'size vs daily trading · penalty only above 3×', f.adov != null ? f.adov + '×' : '—', f.cdov, 15)}
    ${srow('Price run-up into its unlock dates', 'pump-and-dump guard · penalty only above +25%', f.aru != null ? (f.aru >= 0 ? '+' : '') + f.aru + '%' : '—', f.cru, 10)}
    ${srow('Experience bonus', '½ point per IPO anchored, max 10 IPOs', f.deals + ' IPOs', f.cdl, 5)}
    <div class="stot"><span>Total score</span><span style="font-family:'IBM Plex Mono',monospace">${f.score}</span></div>
    <div class="fnote">60 or more = STICKY · under 45 = FLIPPER · in between = NEUTRAL.
    The fewer unlocks watched (${f.n} here), the softer you should hold this verdict — grades firm up automatically as more of this fund's unlocks pass.</div>`;
}
function spark(f){
  const pts = f.ev.map(e => e.sc);
  if(pts.length < 2) return '';
  const min = Math.min(Math.min(...pts), 50), max = Math.max(Math.max(...pts), 50);
  const W = 540, H = 64, P = 6;
  const x = i => P + i * (W - 2 * P) / (pts.length - 1);
  const y = v => H - P - (v - min) * (H - 2 * P) / ((max - min) || 1);
  const line = pts.map((v, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1)).join(' ');
  return `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:64px;display:block;margin:6px 0 2px" preserveAspectRatio="none">
    <line x1="${P}" y1="${y(50).toFixed(1)}" x2="${W-P}" y2="${y(50).toFixed(1)}" stroke="rgba(179,111,0,.45)" stroke-dasharray="3 4" stroke-width="1"></line>
    <path d="${line}" fill="none" stroke="#1A2130" stroke-width="1.8"></path>
    <circle cx="${x(pts.length-1).toFixed(1)}" cy="${y(pts[pts.length-1]).toFixed(1)}" r="3" fill="#B36F00"></circle></svg>`;
}
function histBody(f){
  const rows = f.ev.slice().reverse().map(e => {
    const dc = e.dl == null ? '<span class="dl" style="color:#727B8A">start</span>'
      : `<span class="dl" style="color:${e.dl >= 0 ? '#0B8A4D' : '#E24B4A'}">${e.dl >= 0 ? '+' : ''}${e.dl}</span>`;
    const rc = e.r5 == null ? '<span class="hr">—</span>'
      : `<span class="hr" style="color:${e.r5 < 0 ? '#E24B4A' : '#0B8A4D'}">${e.r5 >= 0 ? '+' : ''}${e.r5}%</span>`;
    return `<div class="hrow"><span class="hd">${e.d}</span><span class="hco">${e.co}<span class="ht">${e.t}</span></span>${rc}<span class="hs">${e.sc}</span>${dc}</div>`;
  }).join('');
  const mom = f.nw ? '<b>new</b> — its whole measured record is inside the last 90 days'
    : (f.mom == null ? '—' : `<b style="color:${f.mom > 0 ? '#0B8A4D' : (f.mom < 0 ? '#E24B4A' : '#3F4756')}">${f.mom >= 0 ? '+' : ''}${f.mom} points in the last 90 days</b>`);
  const pend = f.pend && f.pend.length ? `<div class="fnote"><b>Anchored, no unlock measured yet:</b> ${f.pend.join(' · ')}</div>` : '';
  return `${spark(f)}
    <div class="fsub" style="margin:0 0 6px">score trail after every unlock, oldest → newest · dotted line = 50 · trend: ${mom}</div>
    <div class="hrow hhead"><span>date</span><span>IPO · unlock</span><span>week after</span><span>score</span><span>points</span></div>
    ${rows}${pend}
    <div class="fnote">"points" = how much that single unlock moved this fund's score when it happened (newest first).
    Early unlocks swing the score hard — that is normal; it settles as more pass.
    The trail carries today's experience bonus throughout, so its last point matches the score in the table.</div>`;
}
function openFund(i, mode){
  mode = mode || 'score';
  const f = FDATA[i];
  const [bg, fg] = gcol[f.grade];
  const head = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">
      <div><h3>${f.fund}</h3><div class="fsub">${f.deals} IPOs anchored · ${f.n} unlocks watched · score ${f.score}
        <span style="background:${bg};color:${fg};padding:2px 10px;border-radius:99px;font-size:10.5px;font-weight:700;margin-left:4px">${f.grade}</span></div></div>
      <button onclick="document.getElementById('fback').classList.remove('on')" style="border:1px solid rgba(24,33,51,.2);background:#fff;border-radius:8px;padding:5px 11px;font-size:11px;cursor:pointer;color:#3F4756">✕ esc</button>
    </div>
    <div class="fpts">${f.pts.map(p => '<div class="fpt">' + p + '</div>').join('')}</div>
    <div class="ftabs">
      <button class="ftabbtn ${mode === 'score' ? 'on' : ''}" data-m="score">how the score is built</button>
      <button class="ftabbtn ${mode === 'hist' ? 'on' : ''}" data-m="hist">IPO history &amp; trend</button>
    </div>`;
  const card = document.getElementById('fcard');
  card.innerHTML = head + (mode === 'hist' ? histBody(f) : scoreBody(f));
  card.querySelectorAll('.ftabbtn').forEach(btn => btn.onclick = () => openFund(i, btn.dataset.m));
  document.getElementById('fback').classList.add('on');
}
document.getElementById('ftab').addEventListener('click', e => {
  const td = e.target.closest('td.fname');
  if(td) openFund(+td.dataset.fi);
});
document.querySelectorAll('.mrow').forEach(m => m.onclick = () => openFund(+m.dataset.fi, 'hist'));
document.getElementById('fback').addEventListener('click', e => { if(e.target.id === 'fback') e.target.classList.remove('on'); });
document.addEventListener('keydown', e => { if(e.key === 'Escape') document.getElementById('fback').classList.remove('on'); });
})();
</script>
</body></html>"""

os.makedirs("docs", exist_ok=True)
_anch = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Unlock Radar — anchor ranks</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>body{{background:#F7F5F0;color:#1A2130;font-family:'Instrument Sans',system-ui,sans-serif;font-size:15px;max-width:1360px;margin:0 auto;padding:32px 24px 60px}}
h1{{font-family:Fraunces,serif;font-weight:400;font-size:36px;margin-bottom:4px}}h1 em{{font-style:italic;color:#B36F00}}
.sub{{font-size:12.5px;color:#727B8A;margin:6px 0 20px;line-height:1.8}}
{_NAVCSS}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid rgba(24,33,51,.16);border-radius:12px;overflow:hidden;font-size:12.5px}}
th{{text-align:left;font-size:10px;letter-spacing:.12em;color:#727B8A;padding:9px 11px;border-bottom:1px solid rgba(24,33,51,.16);background:#F1EEE6}}
td{{padding:9px 11px;border-bottom:1px solid rgba(24,33,51,.08);font-family:'IBM Plex Mono',monospace}}
tr:last-child td{{border-bottom:0}}
.card{{background:#fff;border:1px solid rgba(24,33,51,.16);border-radius:12px;padding:16px 18px;font-size:12.5px;color:#3F4756;line-height:1.9;margin-bottom:22px}}
.note{{font-size:11.5px;color:#727B8A;line-height:1.9;margin-top:22px;border-top:1px solid rgba(24,33,51,.16);padding-top:13px}}
.cap{{font-size:12px;color:#727B8A;line-height:1.7}} b{{font-weight:600}} i{{font-style:italic}}
.ftools{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 12px}}
#fq{{background:#fff;border:1px solid rgba(24,33,51,.2);border-radius:9px;padding:8px 12px;font-family:'Instrument Sans',sans-serif;font-size:13px;min-width:190px;outline:none;color:#1A2130}}
#fq:focus{{border-color:#B36F00}}
.vpill{{border:1px solid rgba(24,33,51,.2);background:#fff;border-radius:99px;padding:5px 13px;font-size:10.5px;font-weight:700;letter-spacing:.08em;color:#727B8A;cursor:pointer}}
.vpill.on{{background:#1A2130;color:#fff;border-color:#1A2130}}
.fchk{{font-size:11.5px;color:#727B8A;display:flex;align-items:center;gap:5px;cursor:pointer}}
th{{cursor:pointer;user-select:none;vertical-align:bottom}}
th:hover{{background:#EAE6DA}}
th.sa::after{{content:' ▲';color:#B36F00}}th.sd::after{{content:' ▼';color:#B36F00}}
.lay{{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:26px;align-items:start}}
.lay>aside{{order:2;position:sticky;top:18px;display:flex;flex-direction:column;gap:13px}}
.lay>aside .card{{margin-bottom:0}}
.lay>.main{{order:1;min-width:0;overflow-x:auto}}
@media(max-width:1020px){{.lay{{grid-template-columns:1fr}}.lay>aside{{position:static;order:0}}.lay>.main{{order:0}}}}</style></head><body>
{NAV.format(a="", b="on", c="")}
<h1>Anchor <em>ranks</em></h1>
<div class="sub">{len(FUND_TABLE)} funds graded · {len(_deal_counts)} funds tracked in total · unlock history covers <b>{_WINDOW}</b> · updated {gen_label}</div>
<div class="lay">
<aside class="rail">
<div class="card"><b>What this page tells you.</b> Anchor funds get shares before the IPO and are freed to sell 30/90 days later.
Some funds' stocks routinely <i>fall</i> right after their lock-ins open — a sign they take profits and leave. Others hold, and their stocks stay stable.
This page grades each fund on that behaviour, using only what actually happened to prices — no opinions.</div>
<div class="card"><b>Reading a row:</b> "Vikasa · 33 IPOs · 25 watched · +1.1% · 48%" means: Vikasa anchored 33 of our tracked IPOs; 25 of its unlocks have passed;
the typical stock moved +1.1% in the week after; and 48 out of 100 fell. That is average behaviour → NEUTRAL.<br><br>
<b>Why can "unlocks watched" exceed "IPOs anchored"?</b> Every IPO creates <i>two</i> anchor unlocks — one at 30 days, one at 90 days.
So a fund with 4 IPOs can have up to 8 unlocks; we count only the ones whose date has already passed.</div>
<div class="card"><b>The verdict:</b> <b>STICKY</b> = stocks usually hold up after their unlocks (friendlier to stay invested through).
<b>FLIPPER</b> = stocks usually drop after their unlocks (be careful holding through their unlock dates). NEUTRAL = in between.
A fund needs at least 3 measured unlocks to get a verdict.</div>
<div class="card"><b>Rising or slipping?</b> We rebuild every fund's score after each of its unlocks, oldest to newest.
The <b>trend 90d</b> column and the movers cards show how many points the score moved in the last 90 days —
▲ means its recent unlocks improved its record, ▼ means they hurt it. "new" = the fund's whole measured record
is younger than 90 days, so there is no earlier self to compare against. Click any fund name for its unlock-by-unlock trail.</div>
<div class="card" style="background:#FBF0DA;border-color:rgba(179,111,0,.3)"><b>Coverage note.</b> 2026 fund lists are complete. For 2024–25 the source
(Chittorgarh) publicly shows only each year's top-5 funds — the rest sits behind their paid product. So older history is thin for smaller funds;
coverage completes automatically day by day from here on.</div>
</aside>
<div class="main">
{_MOVERS}
<div class="ftools">
  <input id="fq" placeholder="search fund house&hellip;">
  <span class="vpill on" data-v="ALL">ALL</span>
  <span class="vpill" data-v="STICKY">STICKY</span>
  <span class="vpill" data-v="NEUTRAL">NEUTRAL</span>
  <span class="vpill" data-v="FLIPPER">FLIPPER</span>
  <label class="fchk"><input type="checkbox" id="fmin"> only well-tested (10+ unlocks watched)</label>
  <span style="margin-left:auto;font-size:11px;color:#727B8A">click any column heading to sort</span>
</div>
<table id="ftab"><tr><th>#</th><th>fund house</th><th>IPOs anchored</th><th>unlocks watched</th><th>typical move after unlock</th><th>fell how often</th><th>listing-day gain</th><th>gain today</th><th>size vs daily vol</th><th>verdict</th><th>trend 90d</th></tr>{_frows if _frows else "<tr><td colspan=11 style='color:#727B8A'>Grades appear once the historical backfill completes and anchor names finish syncing.</td></tr>"}</table>
<h2 style="font-family:Fraunces,serif;font-style:italic;font-weight:430;font-size:18px;color:#3F4756;margin:26px 0 8px">Tracked but not yet graded</h2>
<p class="cap" style="font-size:12px;color:#727B8A;margin:0 0 8px">Every other fund in the registry, with its deal count in brackets — too few finished unlocks to judge yet. They graduate to the table above automatically.</p>
<div style="font-size:12px;color:#727B8A;line-height:2">{_urows}</div>
<div class="note">A FLIPPER verdict means stocks this fund anchored typically fell after unlock days — a pattern across their deals, not proof the fund itself sold.
The more "unlocks watched", the more the verdict means. Fund lists come from public allotment disclosures. Not investment advice.</div>
</div>
</div>
""" + _ANCH_JS.replace("__FD__", json.dumps(_FDATA))
with open("docs/anchors.html", "w", encoding="utf-8") as _f:
    _f.write(_anch)

def _tbl(title, headers, rows, caption=""):
    h = "".join(f"<th>{x}</th>" for x in headers)
    b = "".join("<tr>" + "".join(f"<td>{('—' if c is None else c)}</td>" for c in row) + "</tr>" for row in rows)
    cap = f"<p class='cap'>{caption}</p>" if caption else ""
    return f"<h2>{title}</h2>{cap}<table><tr>{h}</tr>{b}</table>"

_tname = {"A30": "30D anchor", "A90": "90D anchor", "PRE6M": "6M pre-IPO", "PX1Y": "1Y promoter", "PX2Y": "2Y promoter"}
_typ_rows = []
for _t in ("A30", "A90", "PRE6M", "PX1Y", "PX2Y"):
    _v = _by_type.get(_t, [])
    if _v:
        _typ_rows.append((_tname[_t], len(_v), _sgn(_med(_v)), f"{round(sum(1 for x in _v if x < 0) / len(_v) * 100)}%"))
_dov_rows = _bucket_rows(lambda o: o.get("dov_ev"), [("under 1× vol", 0, 1), ("1–5× vol", 1, 5), ("over 5× vol", 5, 10_000)], True)
_pl_rows = _bucket_rows(lambda o: o.get("pl_at_unlock"), [("underwater at unlock", -10_000, 0), ("0–50% gain", 0, 50), ("over 50% gain", 50, 100_000)], True)
_ru_rows = _bucket_rows(lambda o: o.get("runup20"), [("fell into unlock", -10_000, 0), ("0–25% run-up", 0, 25), ("over 25% run-up", 25, 100_000)], True)
_n_total = sum(1 for o in _outs.values() if _r5(o) is not None)

os.makedirs("docs", exist_ok=True)
_bt = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Unlock Radar — backtest</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>body{{background:#F7F5F0;color:#1A2130;font-family:'Instrument Sans',system-ui,sans-serif;font-size:15px;max-width:1360px;margin:0 auto;padding:36px 24px 60px}}
h1{{font-family:Fraunces,serif;font-weight:400;font-size:38px}}h1 em{{font-style:italic;color:#B36F00}}
.sub{{font-size:12.5px;color:#727B8A;margin-top:6px;line-height:1.8}}.sub a{{color:#0E7490}}
h2{{font-family:Fraunces,serif;font-style:italic;font-weight:430;font-size:19px;color:#3F4756;margin:30px 0 10px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid rgba(24,33,51,.16);border-radius:12px;overflow:hidden;font-size:13px}}
th{{text-align:left;font-size:10.5px;letter-spacing:.14em;color:#727B8A;padding:9px 13px;border-bottom:1px solid rgba(24,33,51,.16);background:#F1EEE6}}
td{{padding:9px 13px;border-bottom:1px solid rgba(24,33,51,.08);font-family:'IBM Plex Mono',monospace;font-size:12.5px}}
td:first-child{{font-family:'Instrument Sans',sans-serif;font-weight:500}}\n{_NAVCSS}
tr:last-child td{{border-bottom:0}}
.note{{font-size:11.5px;color:#727B8A;line-height:1.9;margin-top:26px;border-top:1px solid rgba(24,33,51,.16);padding-top:14px}}
.card{{background:#fff;border:1px solid rgba(24,33,51,.16);border-radius:12px;padding:15px 18px;font-size:13px;color:#3F4756;line-height:1.9;margin:4px 0 8px}}
.cap{{font-size:12px;color:#727B8A;margin:-4px 0 8px;line-height:1.7}}
b{{font-weight:600}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:6px 30px;align-items:start;margin-top:14px}}
.grid2 .card{{margin:4px 0 0}}
@media(max-width:1020px){{.grid2{{grid-template-columns:1fr}}}}</style></head><body>
{NAV.format(a="", b="", c="on")}\n<h1>Unlock <em>backtest</em></h1>
<div class="sub">{_n_total} past unlock events measured, covering <b>{_WINDOW}</b> · official BSE/NSE closing prices · refreshed daily, last: {gen_label} · <a href="index.html">← back to the radar</a></div>
<div class="grid2">
<div class="card"><b>How to read this page.</b> For every lock-in that opened in the past, we noted the share price just before the unlock day and again 5 trading days later.
<b>"Typical move"</b> is the middle result — half the stocks did better, half did worse (one crazy stock can't distort it).
<b>"Fell how often"</b> is simply: out of 100 such unlocks, how many stocks were lower a week later.</div>
<div class="card"><b>Example:</b> a row reading "90D anchor · 53 · −1.9% · 58%" means: we watched 53 ninety-day unlocks; the typical stock was down 1.9% a week later; 58 out of 100 fell. So 90-day unlocks have been bad news on average.</div>
<div>{_tbl("Does the type of unlock matter?", ["unlock type", "events watched", "typical move, 5 days later", "fell how often"], _typ_rows,
      "Each row is one kind of unlock. We watched every one that happened and checked the share price 5 trading days later.")}</div>
<div>{_tbl("Does size vs liquidity matter?", ["how big vs daily trading", "events watched", "typical move, 5 days later", "fell how often"], _dov_rows,
      "An unlock of 5× daily trading means the shares set free equal five normal days of all buying and selling — heavy supply to digest.")}</div>
<div>{_tbl("Does the holders' profit matter?", ["holders' profit on unlock eve", "events watched", "typical move, 5 days later", "fell how often"], _pl_rows,
      "If holders sit on big profits when their lock-in opens, are they more tempted to sell? This table checks exactly that.")}</div>
<div>{_tbl("Does a price run-up before the unlock matter?", ["price move in the 20 days before", "events watched", "typical move, 5 days later", "fell how often"], _ru_rows,
      "Sometimes a stock rallies suspiciously into an unlock date. This checks what usually happens next.")}</div>
</div>
<div class="note">Simple rule for the whole page: <b>the more "events watched", the more you can trust the row.</b> Under ~20 events, treat it as a hint, not a fact.
Pre-IPO/promoter dates are computed from SEBI rules (can be off by a few days). Not investment advice.</div>
</body></html>"""
with open("docs/backtest.html", "w", encoding="utf-8") as _f:
    _f.write(_bt)

FUND_COUNTS = dict(_deal_counts)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unlock Radar — SME IPO lock-in expiries</title>
<meta name="description" content="Daily-refreshed anchor, pre-IPO and promoter lock-in expiries for Indian SME IPOs, with market context.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..700;1,9..144,300..700&family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#F7F5F0; --panel:#FFFFFF; --panel2:#F1EEE6; --line:rgba(24,33,51,.09); --line2:rgba(24,33,51,.16);
  --txt:#1A2130; --mut:#727B8A; --mut2:#3F4756;
  --amber:#B36F00; --amber-bg:#FBF0DA; --cyan:#0E7490; --cyan-bg:#DFF2F6; --violet:#6D4FD1; --violet-bg:#EEE9FC;
  --coral:#CE4E14; --coral-bg:#FCE9DE; --red:#D6273B; --red-bg:#FBE4E7; --green:#0B8A4D;
  --mono:"IBM Plex Mono",ui-monospace,monospace;
}
*{margin:0;padding:0;box-sizing:border-box}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--txt);font-family:"Instrument Sans",system-ui,sans-serif;font-size:15px;min-height:100vh;padding-bottom:60px;
  background-image:radial-gradient(1100px 500px at 15% -10%, rgba(179,111,0,.05), transparent 60%)}
.wrap{max-width:980px;margin:0 auto;padding:0 24px}
a{color:inherit;text-decoration:none}
.sec{font-size:12px;font-weight:600;letter-spacing:.05em;color:var(--mut2);margin:26px 0 10px;display:flex;align-items:center;gap:7px}
.sec .hint{color:var(--mut);cursor:help;font-size:13px}
::selection{background:rgba(179,111,0,.22)}
.topnav{display:flex;gap:8px;padding-top:22px}.topnav a{padding:7px 16px;border:1px solid var(--line2);border-radius:99px;font-size:12px;font-weight:600;color:var(--mut2);background:var(--panel)}.topnav a.on{background:var(--txt);color:#fff;border-color:var(--txt)}
.mast{display:flex;justify-content:space-between;align-items:flex-end;gap:14px;padding:20px 0 16px;border-bottom:1.5px solid var(--line2);flex-wrap:wrap}
h1{font-family:Fraunces,serif;font-weight:400;font-size:clamp(34px,5vw,46px);line-height:1}
h1 em{font-style:italic;color:var(--amber)}
.subline{font-size:12px;color:var(--mut);margin-top:6px}
.subline a{color:var(--cyan);border-bottom:1px dotted rgba(14,116,144,.5)}
.glance{font-family:var(--mono);font-size:12.5px;color:var(--mut2);text-align:right;line-height:2}
.glance b{font-weight:600}
.glance .rd{color:var(--red)}
.wrow{display:flex;align-items:center;gap:12px;padding:11px 12px;border-bottom:1px solid var(--line);background:var(--panel);cursor:pointer;transition:background .15s}
.wrow:first-of-type{border-top-left-radius:12px;border-top-right-radius:12px}
.wrow:last-of-type{border-bottom-left-radius:12px;border-bottom-right-radius:12px;border-bottom:0}
.wbox{border:1px solid var(--line2);border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(16,24,40,.05)}
.wrow:hover{background:#FBFAF7}
.wrow.today{border-left:3px solid var(--red)}
.wd{font-family:var(--mono);font-size:11px;font-weight:600;color:var(--mut);width:52px;text-align:center}
.wrow.today .wd{color:var(--red)}
.wmain{flex:1;min-width:0}
.wname{font-size:14px;font-weight:600}
.wname .pl{font-family:var(--mono);font-size:11px;font-weight:500;margin-left:7px}
.wsub{font-size:11.5px;color:var(--mut);margin-top:1px}
.pill{display:inline-block;font-size:10.5px;letter-spacing:.06em;padding:2px 9px;border-radius:99px;font-weight:600;white-space:nowrap}
.p30{background:var(--amber-bg);color:var(--amber)} .p90{background:var(--cyan-bg);color:var(--cyan)}
.p6m{background:var(--violet-bg);color:var(--violet)} .ppx{background:var(--coral-bg);color:var(--coral)}
.pmb{background:#E8ECF5;color:#4A5A7A}
.wnum{text-align:right;font-family:var(--mono);min-width:86px}
.wnum .v{font-size:13px;font-weight:600}
.wnum .s{font-size:10.5px;margin-top:1px}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:3px}
.dgreen{color:var(--green)}.damber{color:var(--amber)}.dred{color:var(--red)}
.bgreen{background:#0B8A4D}.bamber{background:#EF9F27}.bred{background:#E24B4A}
.pb{border:1px solid var(--line2);border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(16,24,40,.05)}
.pbrow{display:flex;align-items:center;gap:12px;padding:10px 14px;border-bottom:1px solid var(--line);background:var(--panel);cursor:pointer}
.pbrow:last-child{border-bottom:0}
.pbrow:hover{background:#FBFAF7}
.pbrank{font-family:var(--mono);font-size:11px;color:var(--mut);width:14px}
.pbname{flex:1;font-size:13.5px;font-weight:600;min-width:0}
.pbname span{font-family:var(--mono);font-size:11px;color:var(--mut);font-weight:400;margin-left:7px}
.pbcap{font-family:var(--mono);font-size:11.5px;color:var(--mut2);width:74px;text-align:right}
.pbdov{font-family:var(--mono);font-size:13px;font-weight:600;width:86px;text-align:right}
.legend{font-size:11px;color:var(--mut);margin-top:7px}
.hzrow{display:flex;align-items:center;gap:14px;margin-bottom:8px}
.hzrow label{font-size:12px;font-weight:600;color:var(--mut2)}
.hzrow input[type=range]{flex:1;accent-color:var(--amber);height:4px}
.hzout{font-family:var(--mono);font-size:12px;min-width:100px;text-align:right;color:var(--mut2)}
.strip{position:relative;height:34px;border-top:2px solid var(--line2);margin:12px 6px 0}
.sdot{position:absolute;top:-6px;width:10px;height:10px;border-radius:50%;transform:translateX(-50%);cursor:pointer;border:2px solid #fff;box-shadow:0 0 0 1px var(--line2)}
.snow{position:absolute;top:-9px;width:3px;height:16px;background:var(--red);transform:translateX(-50%)}
.saxis{display:flex;justify-content:space-between;font-size:10px;font-family:var(--mono);color:var(--mut);margin-top:4px}
.i-a30{background:#EF9F27}.i-a90{background:#14A38B}.i-pre{background:#7F77DD}.i-px{background:#D85A30}
.toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:22px 0 12px;padding-top:16px;border-top:1px solid var(--line)}
#search{background:var(--panel);border:1px solid var(--line2);border-radius:99px;color:var(--txt);font-family:inherit;font-size:12.5px;padding:8px 15px;width:190px;outline:none}
#search:focus{border-color:var(--amber)}
.fdot{display:flex;align-items:center;gap:5px;font-size:11.5px;font-weight:600;color:var(--mut2);cursor:pointer;user-select:none;padding:4px 2px}
.fdot i{width:9px;height:9px;border-radius:50%;display:inline-block}
.fdot.off{opacity:.35}
.tabs{display:flex;border:1px solid var(--line2);border-radius:9px;overflow:hidden;margin-left:auto;background:var(--panel)}
.tab{padding:6px 14px;font-size:11px;font-weight:600;letter-spacing:.06em;color:var(--mut);cursor:pointer;background:transparent;border:0;font-family:inherit}
.tab.on{background:var(--txt);color:#fff}
.mb-toggle{display:flex;gap:6px;align-items:center;font-size:11.5px;color:var(--mut2);cursor:pointer}
.mb-toggle input{accent-color:var(--amber)}
.lrow{display:flex;align-items:center;gap:12px;padding:8px 6px;border-bottom:1px solid var(--line);cursor:pointer}
.lrow:hover{background:#FBFAF7}
.lrow.past{opacity:.5}
.ld{font-family:var(--mono);font-size:12px;color:var(--mut2);width:56px}
.lco{flex:1;font-size:13px;font-weight:500;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lco .pl{font-family:var(--mono);font-size:10.5px;margin-left:6px;font-weight:500}
.lnum{font-family:var(--mono);font-size:12px;color:var(--mut2);width:78px;text-align:right}
.empty{color:var(--mut);padding:24px 4px;font-size:12.5px}
mark{background:rgba(179,111,0,.25);border-radius:3px}
.mback{position:fixed;inset:0;background:rgba(26,33,48,.45);backdrop-filter:blur(6px);display:none;z-index:200;align-items:center;justify-content:center;padding:20px}
.mback.on{display:flex}
.mcard{background:var(--panel);border:1px solid var(--line2);border-radius:18px;max-width:760px;width:100%;max-height:88vh;overflow-y:auto;padding:26px 28px 22px;box-shadow:0 24px 60px rgba(16,24,40,.25);scrollbar-width:thin;animation:mup .25s cubic-bezier(.2,.9,.3,1)}
@keyframes mup{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:none}}
.mhead{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;border-bottom:1px solid var(--line);padding-bottom:13px}
.mhead h3{font-family:Fraunces,serif;font-style:italic;font-weight:430;font-size:24px;line-height:1.2}
.msub{font-size:11.5px;color:var(--mut);margin-top:6px;line-height:1.9;font-family:var(--mono)}
.pxchip{font-weight:600}
.mx{background:var(--panel);border:1px solid var(--line2);color:var(--mut2);border-radius:9px;font-family:inherit;font-size:12px;font-weight:600;padding:6px 11px;cursor:pointer}
.mx:hover{border-color:var(--red);color:var(--red)}
.mgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin:15px 0 4px}
.mstat{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.mstat .k{font-size:9px;font-weight:700;letter-spacing:.14em;color:var(--mut)}
.mstat .v{font-family:var(--mono);font-size:14px;font-weight:600;margin-top:4px}
.mstat .v small{font-size:10px;color:var(--mut);font-weight:400}
.msec{font-size:10px;font-weight:700;letter-spacing:.2em;color:var(--mut);margin:18px 0 9px}
.cbar{display:flex;height:24px;border-radius:8px;overflow:hidden;border:1px solid var(--line2);margin-top:4px}
.cseg{height:100%}
i.cmpc,.cseg.cmpc{background:#99A1B0} i.cexc,.cseg.cexc{background:#D85A30} i.cpre,.cseg.cpre{background:#7F77DD} i.cpub,.cseg.cpub{background:#D4DBE6}
.clegend{display:flex;gap:13px;flex-wrap:wrap;margin-top:7px;font-size:10.5px;color:var(--mut);font-family:var(--mono)}
.clegend i{display:inline-block;width:9px;height:9px;border-radius:3px;margin-right:4px;vertical-align:-1px}
.tl{position:relative;height:56px;margin:8px 2px 0}
.tlline{position:absolute;top:16px;left:0;right:0;height:2px;background:var(--line2)}
.tld{position:absolute;top:11px;width:12px;height:12px;border-radius:50%;border:2.5px solid #fff;box-shadow:0 0 0 1px var(--line2);transform:translateX(-50%)}
.tld.b30{background:#EF9F27}.tld.b90{background:#14A38B}.tld.bpre{background:#7F77DD}.tld.bpx{background:#D85A30}
.tld.done{opacity:.35}
.tlnow{position:absolute;top:5px;width:2.5px;height:24px;background:var(--red);transform:translateX(-50%)}
.tll{position:absolute;top:32px;font-size:9.5px;color:var(--mut);font-family:var(--mono);line-height:1.5;white-space:nowrap}
.mtabs{display:flex;gap:8px;margin:18px 0 10px}
.mtab{border:1px solid var(--line2);background:var(--panel2);border-radius:99px;padding:6px 15px;font-family:'Instrument Sans',sans-serif;font-size:10.5px;font-weight:700;letter-spacing:.1em;color:var(--mut);cursor:pointer}
.mtab.on{background:#1A2130;color:#fff;border-color:#1A2130}
.hrow{display:flex;gap:7px;margin-top:9px;flex-wrap:wrap}
.hbox{flex:1;min-width:76px;background:var(--panel2);border-radius:9px;padding:6px 9px;text-align:center}
.hk{font-size:9px;font-weight:700;letter-spacing:.12em;color:var(--mut)}
.hv{font-family:var(--mono);font-size:13.5px;font-weight:600;margin-top:2px}
.hcmp{font-size:11.5px;color:var(--mut2);margin-top:9px;line-height:1.7;border-top:1px dashed var(--line2);padding-top:7px}
.mev{border:1px solid var(--line);border-left-width:3.5px;border-radius:10px;padding:11px 14px;margin-bottom:8px;background:#FDFCFA}
.mev.b30{border-left-color:#EF9F27}.mev.b90{border-left-color:#14A38B}.mev.bpre{border-left-color:#7F77DD}.mev.bpx{border-left-color:#D85A30}
.mev .top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.mev .top b{font-size:13.5px;font-weight:600}
.mev .num2{font-size:12px;color:var(--mut2);font-family:var(--mono)}
.mev .how{font-size:12px;color:var(--mut2);line-height:1.85;margin-top:7px;border-top:1px dashed var(--line2);padding-top:7px}
.mev .how .fl{display:block}
.mev .how b{color:var(--txt);font-weight:600;font-family:var(--mono);font-size:11.5px}
.mev .how .lbl{display:inline-block;min-width:42px;font-weight:700;color:var(--mut);font-size:10px;letter-spacing:.08em}
.emkt{font-size:12px;color:var(--mut2);margin-top:7px;font-family:var(--mono)}
.efrow{display:flex;align-items:center;gap:10px;margin-top:6px}
.etrack{flex:1;height:8px;background:var(--panel2);border:1px solid var(--line);border-radius:99px;overflow:hidden}
.efill{height:100%;border-radius:99px}
.efill.b30{background:#EF9F27}.efill.b90{background:#14A38B}.efill.bpre{background:#7F77DD}.efill.bpx{background:#D85A30}
.efill.dv.dgreen{background:#0B8A4D}.efill.dv.damber{background:#EF9F27}.efill.dv.dred{background:#E24B4A}
.eflab{font-size:10px;color:var(--mut);font-family:var(--mono);white-space:nowrap}
.fund{display:inline-block;background:var(--panel2);border:1px solid var(--line);border-radius:99px;padding:3px 10px;font-size:11px;color:var(--mut2);margin:0 6px 6px 0}
.fund b{color:var(--coral);font-weight:600;font-family:var(--mono);font-size:10px}
.mnote{font-size:11px;color:var(--mut);line-height:1.8;margin-top:14px;border-top:1px solid var(--line);padding-top:11px}
.mbtns{display:flex;gap:10px;margin-top:14px}
.mbtn{border-radius:10px;padding:10px 17px;font-family:inherit;font-size:12.5px;font-weight:700;cursor:pointer}
.mbtn.primary{background:var(--txt);color:#fff;border:0}
.mbtn.ghost{background:transparent;border:1px solid var(--line2);color:var(--mut2)}
footer{border-top:1px solid var(--line2);margin-top:44px;padding-top:18px;font-size:11.5px;color:var(--mut);line-height:1.9;display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
footer b{color:var(--mut2);font-weight:600}
@media(max-width:760px){
  .glance{text-align:left}
  .mgrid{grid-template-columns:1fr 1fr}
  .pbcap{display:none}
  .wnum{min-width:70px}
  .tabs{margin-left:0}
}
</style>
</head>
<body>
<div class="wrap">

<div class="topnav"><a href="index.html" class="on">Radar</a><a href="anchors.html">Anchor ranks</a><a href="backtest.html">Backtest</a></div>
<header class="mast">
  <div>
    <h1>Unlock <em>Radar</em></h1>
    <div class="subline">SME lock-in expiries · refreshed daily 07:00 IST · <a href="lockins.ics">calendar feed</a> · <a href="data.json">raw json</a> · <a href="backtest.html">backtest</a> · data as of __GENERATED__</div>
  </div>
  <div class="glance" id="glance"></div>
</header>

<div class="sec" id="weekhead">This week</div>
<div class="wbox" id="week"></div>

<div class="sec">Pressure board — heaviest unlocks ahead <span class="hint" title="Next 90 days, ranked by unlocking shares vs average daily traded volume">ⓘ</span></div>
<div class="pb" id="pboard"></div>
<div class="legend"><span class="dot bgreen"></span> under 1× easily absorbed &nbsp; <span class="dot bamber"></span> 1–5× heavy &nbsp; <span class="dot bred"></span> over 5× supply cliff</div>

<div class="sec" style="margin-top:30px">Just passed — how those unlocks actually went <span class="hint" title="Events from the last 30 days: the stock's move 5 trading days after the unlock, coloured green/red. Click a row for full history.">ⓘ</span></div>
<div class="wbox" id="jpast"></div>

<div class="sec" style="margin-top:30px">Horizon</div>
<div class="hzrow">
  <input type="range" min="15" max="180" step="15" value="60" id="hz">
  <span class="hzout" id="hzout">next 60 days</span>
</div>
<div class="strip" id="strip"></div>
<div class="saxis"><span>today</span><span id="hzend"></span></div>

<div class="toolbar">
  <input id="search" placeholder="search company…" autocomplete="off">
  <span class="fdot" data-f="a30"><i class="i-a30"></i>30D</span>
  <span class="fdot" data-f="a90"><i class="i-a90"></i>90D</span>
  <span class="fdot" data-f="pre"><i class="i-pre"></i>6M</span>
  <span class="fdot" data-f="px"><i class="i-px"></i>PROM</span>
  <label class="mb-toggle"><input type="checkbox" id="mbToggle"> +MB</label>
  <div class="tabs">
    <button class="tab on" data-t="up">UPCOMING</button>
    <button class="tab" data-t="past">PAST</button>
  </div>
</div>
<div id="ledger"></div>

<footer>
  <div><b>Unlock Radar</b> · Chittorgarh.com + BSE/NSE bhavcopy + SEBI ICDR rules · runs itself on GitHub Actions.<br>
  Anchor 50% at 30/90d · pre-IPO non-promoters at 6M (est.) · promoter excess over 20% MPC at 1yr/2yr (est.).</div>
  <div>Estimates are computed, not exchange-confirmed — verify before acting.<br>Research information only — <b>not investment advice</b>.</div>
</footer>

</div>
<div class="mback" id="mback"><div class="mcard" id="mcard"></div></div>
<script>
const DATA = __DATA__;
const STATS = __STATS__;
const OUTS = __OUTS__;
const FUNDS = __FUNDS__;
const REG = __REG__;
const IST_OFF = 330;
function istToday(){
  const n = new Date();
  const ist = new Date(n.getTime() + (n.getTimezoneOffset() + IST_OFF) * 60000);
  return new Date(ist.getFullYear(), ist.getMonth(), ist.getDate());
}
const T0 = istToday();
const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const pd = s => { const [y,m,dd] = s.split('-').map(Number); return new Date(y, m-1, dd); };
const dayDiff = s => Math.round((pd(s) - T0) / 86400000);
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const DOW = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const fmtL = s => { const d = pd(s); return `${DOW[d.getDay()]}, ${String(d.getDate()).padStart(2,'0')} ${MON[d.getMonth()]} ${d.getFullYear()}`; };
const fmtM = s => { const d = pd(s); return `${String(d.getDate()).padStart(2,'0')}-${MON[d.getMonth()]}-${d.getFullYear()}`; };
const fmtS = s => { const d = pd(s); return `${String(d.getDate()).padStart(2,'0')} ${MON[d.getMonth()]}`; };
function shFmt(n){
  if(n == null || n === 0) return '—';
  if(n >= 1e7) return (n/1e7).toFixed(2).replace(/\.?0+$/,'') + ' Cr';
  if(n >= 1e5) return (n/1e5).toFixed(2).replace(/\.?0+$/,'') + ' L';
  return n.toLocaleString('en-IN');
}
const crFmt = v => v == null ? null : '₹' + (v >= 100 ? Math.round(v).toLocaleString('en-IN') : v.toFixed(1)) + ' cr';
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const TYPE = {
  A30:{lbl:'30D', cls:'p30', fam:'a30'}, A90:{lbl:'90D', cls:'p90', fam:'a90'},
  PRE6M:{lbl:'6M PRE-IPO', cls:'p6m', fam:'pre'},
  PX1Y:{lbl:'1Y PROM', cls:'ppx', fam:'px'}, PX2Y:{lbl:'2Y PROM', cls:'ppx', fam:'px'}
};
const TLONG = {A30:'30-day anchor unlock', A90:'90-day anchor unlock', PRE6M:'Pre-IPO holders unlock (6M)', PX1Y:'Promoter release (1 year)', PX2Y:'Promoter release (2 years)'};
const BCLS = {A30:'b30', A90:'b90', PRE6M:'bpre', PX1Y:'bpx', PX2Y:'bpx'};
const FAM_ON = {a30:true, a90:true, pre:true, px:true};
let TAB='up', MB=false, Q='', WIN=60;
const $ = id => document.getElementById(id);
const nfmt = n => n == null ? '—' : n.toLocaleString('en-IN');
const line = (lbl, txt) => `<span class="fl"><span class="lbl">${lbl}</span> ${txt}</span>`;
function dov(e){ return (e.sh && e.r.avg_vol) ? e.sh / e.r.avg_vol : null; }
function dovCls(v){ return v < 1 ? 'dgreen' : v <= 5 ? 'damber' : 'dred'; }
function dovDot(v){ return v < 1 ? 'bgreen' : v <= 5 ? 'bamber' : 'bred'; }
function dovLab(v){ return (v < 10 ? v.toFixed(1) : Math.round(v)) + '×'; }
function mkt(e){ return (e.sh && e.r.last_close) ? e.sh * e.r.last_close / 1e7 : null; }
function plChip(r, small){
  if(r.chg_from_issue_pct == null) return '';
  const up = r.chg_from_issue_pct >= 0;
  return `<span class="pl ${up?'dgreen':'dred'}" title="Last close vs final IPO issue price">${up?'+':''}${r.chg_from_issue_pct}% from IPO price</span>`;
}
function pills(e){
  let h = `<span class="pill ${e.meta.cls}">${e.meta.lbl}</span>`;
  if(e.r.category !== 'SME') h += ` <span class="pill pmb">MB</span>`;
  return h;
}
function events(){
  const out = [];
  for(const r of DATA.records){
    for(const e of (r.events || [])){
      const t = TYPE[e.t]; if(!t || !FAM_ON[t.fam]) continue;
      if(!MB && r.category !== 'SME') continue;
      if(r.category !== 'SME' && t.fam !== 'a30' && t.fam !== 'a90') continue;
      out.push({...e, r, meta:t});
    }
  }
  return out;
}
function explain(e, r){
  const phased = (r.events||[]).some(x => x.t === 'PX2Y');
  const allot = r.boa_date || r.anchor_allotment_date;
  if(e.t === 'A30' || e.t === 'A90'){
    const dd = e.t === 'A30' ? 30 : 90;
    return line('QTY', `50% × <b>${nfmt(r.anchor_shares)}</b> anchor sh = <b>${nfmt(e.sh)}</b> sh`) +
           line('DATE', `allotment + ${dd} days → <b>${fmtM(e.d)}</b> (exchange-published)`);
  }
  if(e.t === 'PRE6M'){
    const q = (r.pre_shares && r.prom_pre_pct != null)
      ? `<b>${nfmt(r.pre_shares)}</b> pre-issue sh × (100 − ${r.prom_pre_pct}%) = <b>${nfmt(r.nonprom_pre_shares)}</b> sh${r.nonprom_pre_pct_of_post ? ` (${r.nonprom_pre_pct_of_post}% of company)` : ''}`
      : `pending — shareholding data syncs on next run`;
    return line('QTY', q) + line('DATE', `allotment ${fmtM(allot)} + 6 months = <b>${fmtM(e.d)}</b> (est., ±few days)`);
  }
  const excPct = r.prom_post_pct != null ? (r.prom_post_pct - 20).toFixed(2) : null;
  if(e.t === 'PX1Y'){
    const q = excPct ? `(${r.prom_post_pct}% − 20% MPC) = ${excPct}% of company${phased ? '; <b>50%</b> releases now' : '; <b>100%</b> releases now'}` : 'pending shareholding data';
    return line('QTY', q) + line('DATE', `allotment ${fmtM(allot)} + 12 months = <b>${fmtM(e.d)}</b> (est.)`) +
           line('RULE', phased ? 'listed on/after 08-Mar-2025 → phased 50/50 release' : 'listed before 08-Mar-2025 → single release at 1yr');
  }
  if(e.t === 'PX2Y')
    return line('QTY', `remaining <b>50%</b> of promoter excess = <b>${nfmt(e.sh)}</b> sh (20% MPC stays locked 3yrs)`) +
           line('DATE', `allotment ${fmtM(allot)} + 24 months = <b>${fmtM(e.d)}</b> (est.)`);
  return '';
}
function capBar(r){
  if(r.prom_post_pct == null || !r.post_shares) return '';
  const mpc = 20, exc = +(r.prom_post_pct - 20).toFixed(2), pre = +(r.nonprom_pre_pct_of_post || 0);
  let pub = +(100 - mpc - Math.max(exc,0) - pre).toFixed(2); if(pub < 0) pub = 0;
  const seg = (w, cls, lb) => w > 0.4 ? `<div class="cseg ${cls}" style="width:${w}%" title="${lb} · ${w}%"></div>` : '';
  return `<div class="msec">CAPITAL STRUCTURE — WHO HOLDS THE COMPANY</div>
  <div class="cbar">${seg(mpc,'cmpc','20% MPC, 3yr lock')}${seg(Math.max(exc,0),'cexc','Promoter excess')}${seg(pre,'cpre','Pre-IPO non-promoter')}${seg(pub,'cpub','IPO float incl. anchors')}</div>
  <div class="clegend"><span><i class="cmpc"></i>MPC ${mpc}%</span><span><i class="cexc"></i>Prom excess ${Math.max(exc,0)}%</span><span><i class="cpre"></i>Pre-IPO ${pre}%</span><span><i class="cpub"></i>IPO float ${pub}%</span></div>`;
}
function timelineViz(r){
  const allot = r.boa_date || r.anchor_allotment_date;
  const evs = (r.events || []);
  if(!allot || !evs.length) return '';
  const t0 = pd(allot).getTime();
  const tend = Math.max(...evs.map(e => pd(e.d).getTime())) + 86400000 * 20;
  const X = t => Math.max(0, Math.min(100, (t - t0) / (tend - t0) * 100)).toFixed(1);
  const now = T0.getTime();
  const dots = evs.map(e => `<i class="tld ${BCLS[e.t]} ${pd(e.d).getTime() < now ? 'done' : ''}" style="left:${X(pd(e.d).getTime())}%" title="${TLONG[e.t]} · ${fmtM(e.d)}"></i>`).join('');
  const today = (now >= t0 && now <= tend) ? `<i class="tlnow" style="left:${X(now)}%"></i>` : '';
  return `<div class="msec">DATE LINE — ALLOTMENT TO FINAL RELEASE</div>
  <div class="tl"><div class="tlline"></div>${dots}${today}
  <span class="tll" style="left:0">${fmtM(allot)}<br>allotment</span>
  <span class="tll" style="left:100%;transform:translateX(-100%);text-align:right">${fmtM(iso(new Date(tend)))}</span></div>`;
}
function evViz(e, r){
  let h = '';
  const mv = mkt({...e, r});
  if(mv != null) h += `<div class="emkt">≈ <b>${crFmt(mv)}</b> at market price ₹${r.last_close}</div>`;
  if(e.pct != null)
    h += `<div class="efrow"><div class="etrack"><div class="efill ${BCLS[e.t]}" style="width:${Math.min(e.pct,100)}%"></div></div><span class="eflab">${e.pct}% of company</span></div>`;
  const dv = (e.sh && r.avg_vol) ? e.sh / r.avg_vol : null;
  if(dv != null){
    const c = dovCls(dv);
    h += `<div class="efrow"><div class="etrack"><div class="efill dv ${c}" style="width:${Math.min(dv/20*100,100)}%"></div></div><span class="eflab ${c}" title="Unlocking shares vs average daily traded volume">${dovLab(dv)} typical daily volume</span></div>`;
  }
  const st = STATS[e.t];
  if(st && st.n >= 5) h += `<div class="emkt" style="font-size:11px">history: median ${st.med >= 0 ? '+' : ''}${st.med}% in 5 sessions after past ${TYPE[e.t].lbl} unlocks (n=${st.n})</div>`;
  return h;
}
function fundsBlock(r){
  const names = (REG[r.slug] || r.anchor_names || []).filter(n => !/investment by/i.test(n));
  if(!names.length) return '';
  const chips = names.map(n => {
    const k = n.replace(/\s+/g,' ');
    const cnt = FUNDS[k] || FUNDS[k.replace(/\w\S*/g, t => t[0].toUpperCase()+t.slice(1).toLowerCase())] || 0;
    return `<span class="fund">${esc(n)}${cnt >= 3 ? ` <b title="Appears as anchor in ${cnt} tracked SME IPOs — serial anchor">×${cnt}</b>` : ''}</span>`;
  }).join('');
  return `<div class="msec">ANCHOR INVESTORS (${names.length}) <span style="letter-spacing:0;font-weight:400">· ×n = deals across tracked SME IPOs</span></div><div>${chips}</div>`;
}
function retBox(lbl, v){
  if(v == null) return '';
  const c = v >= 0 ? 'var(--green)' : 'var(--red)';
  return `<div class="hbox"><div class="hk">${lbl}</div><div class="hv" style="color:${c}">${v >= 0 ? '+' : ''}${v}%</div></div>`;
}
function histCard(e, r){
  const o = OUTS[`${r.slug}|${e.t}`];
  const dd = -dayDiff(e.d);
  const size = [e.sh ? shFmt(e.sh) + ' sh' : null, e.pct != null ? e.pct + '% of company' : null].filter(Boolean).join(' · ');
  let body = '';
  if(o){
    body = `<div class="hrow">${o.pre != null ? `<div class="hbox"><div class="hk">CLOSE BEFORE</div><div class="hv">₹${o.pre}</div></div>` : ''}${retBox('+1 DAY', o.r1)}${retBox('+5 DAYS', o.r5)}${retBox('+20 DAYS', o.r20)}</div>`;
    const st = STATS[e.t];
    if(st && st.n >= 5 && o.r5 != null){
      const diff = o.r5 - st.med;
      const verdict = diff > 2 ? `<b style="color:var(--green)">held up better than typical</b>` : diff < -2 ? `<b style="color:var(--red)">did worse than typical</b>` : `<b>about in line with typical</b>`;
      body += `<div class="hcmp">Benchmark: after a ${TYPE[e.t].lbl} unlock the typical stock moves ${st.med >= 0 ? '+' : ''}${st.med}% in 5 days (${st.n} watched). This one moved ${o.r5 >= 0 ? '+' : ''}${o.r5}% → ${verdict}.</div>`;
    }
  } else {
    body = `<div class="hcmp">Price history for this unlock is still syncing — it appears after the next morning run.</div>`;
  }
  return `<div class="mev ${BCLS[e.t]}">
    <div class="top"><b>${TLONG[e.t]}</b><span class="num2">${fmtL(e.d)} · ${dd}d ago</span></div>
    ${size ? `<div class="num2" style="margin-top:4px">${size}</div>` : ''}${body}</div>`;
}
function mTab(btn, id){
  document.querySelectorAll('.mtab').forEach(b => b.classList.toggle('on', b === btn));
  document.querySelectorAll('.mtabc').forEach(d => d.style.display = d.id === id ? '' : 'none');
}
function openModal(slug, tab){
  const r = DATA.records.find(x => x.slug === slug);
  if(!r) return;
  const evs = (r.events || []).slice().sort((a,b) => a.d.localeCompare(b.d));
  const past = evs.filter(e => dayDiff(e.d) < 0);
  const upc = evs.filter(e => dayDiff(e.d) >= 0);
  const evHtml = upc.map(e => {
    const dd = dayDiff(e.d);
    const when = dd === 0 ? 'TODAY' : dd > 0 ? `D-${dd}` : `${-dd}d ago`;
    const size = [e.sh ? shFmt(e.sh) + ' sh' : null, e.pct != null ? e.pct + '% of company' : null].filter(Boolean).join(' · ') || 'size n/a';
    return `<div class="mev ${BCLS[e.t]}">
      <div class="top"><b>${TLONG[e.t]}</b><span class="num2">${fmtL(e.d)} · ${when}</span></div>
      <div class="num2" style="margin-top:4px">${size}</div>${evViz(e, r)}
      <div class="how">${explain(e, r)}</div></div>`;
  }).join('') || '<div class="empty">no upcoming unlocks — all tracked lock-ins have opened</div>';
  const histHtml = past.slice().reverse().map(e => histCard(e, r)).join('') || '<div class="empty">no unlocks have passed yet</div>';
  const defUp = tab === 'h' ? false : (upc.length > 0 || past.length === 0);
  const mpc = r.post_shares ? Math.round(r.post_shares * 0.2) : null;
  $('mcard').innerHTML = `
    <div class="mhead"><div>
      <h3>${esc(r.company)}</h3>
      <div class="msub">${r.category}${r.nse_symbol ? ' · NSE ' + esc(r.nse_symbol) : ''}${r.bse_code ? ' · BSE ' + r.bse_code : ''}${r.isin ? ' · ' + esc(r.isin) : ''}<br>
      allotted ${r.anchor_allotment_date || '—'} · listed ${r.listing_date || '—'}${r.last_close ? `<br><span class="pxchip">₹${r.last_close}</span> close ${r.close_date}` : ''}${r.chg_from_issue_pct != null ? ` · <span class="pxchip ${r.chg_from_issue_pct >= 0 ? 'dgreen' : 'dred'}" title="Last close vs final IPO issue price ₹${r.issue_px}">${r.chg_from_issue_pct >= 0 ? '+' : ''}${r.chg_from_issue_pct}% from IPO price ₹${r.issue_px}</span>` : ''}</div>
    </div><button class="mx" onclick="closeModal()">✕ esc</button></div>
    <div class="mgrid">
      <div class="mstat"><div class="k">PRE-ISSUE CAPITAL</div><div class="v">${shFmt(r.pre_shares)} <small>sh</small></div></div>
      <div class="mstat"><div class="k">POST-ISSUE CAPITAL</div><div class="v">${shFmt(r.post_shares)} <small>sh</small></div></div>
      <div class="mstat"><div class="k">PROMOTER PRE → POST</div><div class="v">${r.prom_pre_pct != null ? r.prom_pre_pct + '%' : '—'} → ${r.prom_post_pct != null ? r.prom_post_pct + '%' : '—'}</div></div>
      <div class="mstat"><div class="k">NON-PROM PRE-IPO</div><div class="v">${shFmt(r.nonprom_pre_shares)} <small>${r.nonprom_pre_pct_of_post ? '· ' + r.nonprom_pre_pct_of_post + '% of co' : ''}</small></div></div>
      <div class="mstat"><div class="k">ANCHOR ALLOTMENT</div><div class="v">${shFmt(r.anchor_shares)} <small>${r.anchor_investment_cr ? '· ₹' + r.anchor_investment_cr + ' cr' : ''}</small></div></div>
      <div class="mstat"><div class="k">20% MPC (3YR LOCK)</div><div class="v">${shFmt(mpc)} <small>sh</small></div></div>
    </div>
    ${capBar(r)}
    ${timelineViz(r)}
    ${fundsBlock(r)}
    <div class="mtabs">
      <button class="mtab ${defUp ? 'on' : ''}" onclick="mTab(this,'mtabu')">UPCOMING (${upc.length})</button>
      <button class="mtab ${defUp ? '' : 'on'}" onclick="mTab(this,'mtabh')">HISTORY (${past.length})</button>
    </div>
    <div class="mtabc" id="mtabu" style="${defUp ? '' : 'display:none'}">${evHtml}</div>
    <div class="mtabc" id="mtabh" style="${defUp ? 'display:none' : ''}">${histHtml}</div>
    <div class="mnote">Anchor dates are exchange-published; "est." events are computed from prospectus data + SEBI ICDR rules — verify against the listing circular. Volume multiple uses recent tracked sessions; AIF/VC exemptions and ESOPs can change actual free-float.</div>
    <div class="mbtns">
      ${r.url ? `<a class="mbtn primary" href="${r.url}" target="_blank" rel="noopener">Chittorgarh page ↗</a>` : ''}
      <button class="mbtn ghost" onclick="closeModal()">Close</button>
    </div>`;
  $('mback').classList.add('on');
  document.body.style.overflow = 'hidden';
}
function closeModal(){ $('mback').classList.remove('on'); document.body.style.overflow = ''; }
document.addEventListener('click', ev => {
  const t = ev.target.closest('[data-slug]');
  if(t){ ev.preventDefault(); openModal(t.dataset.slug, t.dataset.mtab); return; }
  if(ev.target.id === 'mback') closeModal();
});
document.addEventListener('keydown', ev => { if(ev.key === 'Escape') closeModal(); });

function render(){
  const evs = events();
  const up = evs.filter(e => dayDiff(e.d) >= 0).sort((a,b) => a.d.localeCompare(b.d) || (b.pct||0)-(a.pct||0));
  const past = evs.filter(e => dayDiff(e.d) < 0).sort((a,b) => b.d.localeCompare(a.d));
  const tC = up.filter(e => dayDiff(e.d) === 0).length;
  const w7 = up.filter(e => dayDiff(e.d) <= 7).length;
  const m30 = up.filter(e => dayDiff(e.d) <= 30);
  const big = m30.reduce((mx,e) => (e.pct||0) > (mx.pct||0) ? e : mx, {});
  $('glance').innerHTML = `<span class="${tC ? 'rd' : ''}"><b>${tC}</b> today</span> · <b>${w7}</b> this week · <b>${m30.length}</b> in 30d${big.pct ? ` · biggest <b>${big.pct}%</b> of co` : ''}`;

  const week = up.filter(e => dayDiff(e.d) <= 7);
  $('week').innerHTML = week.map(e => {
    const dd = dayDiff(e.d);
    const mv = mkt(e), dv = dov(e);
    return `<div class="wrow ${dd===0?'today':''}" data-slug="${e.r.slug}">
      <div class="wd">${dd===0 ? 'TODAY' : 'D-'+dd}<br><span style="font-weight:400">${fmtS(e.d)}</span></div>
      <div class="wmain"><div class="wname">${esc(e.r.company)}${plChip(e.r)}</div>
      <div class="wsub">${e.sh ? shFmt(e.sh)+' sh' : ''}${e.pct != null ? ' · '+e.pct+'% of company' : ''}${e.est ? ' · est.' : ''}</div></div>
      ${pills(e)}
      <div class="wnum"><div class="v">${mv != null ? crFmt(mv) : (crFmt(e.val) || (e.pct != null ? e.pct+'%' : '—'))}</div>
      <div class="s ${dv != null ? dovCls(dv) : ''}">${dv != null ? `<span class="dot ${dovDot(dv)}"></span>${dovLab(dv)} vol` : (mv != null ? 'at mkt px' : 'at issue px')}</div></div>
    </div>`;
  }).join('') || '<div class="empty" style="padding:16px 14px">quiet week — nothing unlocking in the next 7 days</div>';

  const pb = up.filter(e => dayDiff(e.d) <= 90 && dov(e) != null).sort((a,b) => dov(b) - dov(a)).slice(0, 6);
  $('pboard').innerHTML = pb.map((e, i) => {
    const dv = dov(e), dd = dayDiff(e.d);
    return `<div class="pbrow" data-slug="${e.r.slug}">
      <span class="pbrank">${i+1}</span>
      <div class="pbname">${esc(e.r.company)}<span>${dd===0 ? 'today' : fmtS(e.d)+' · D-'+dd}</span></div>
      ${pills(e)}
      <span class="pbcap">${e.pct != null ? e.pct+'% of co' : shFmt(e.sh)+' sh'}</span>
      <span class="pbdov ${dovCls(dv)}"><span class="dot ${dovDot(dv)}"></span>${dovLab(dv)}</span>
    </div>`;
  }).join('') || '<div class="empty" style="padding:14px">volume data syncs after the next market session — check back tomorrow</div>';

  const jp = past.filter(e => dayDiff(e.d) >= -30).slice(0, 8);
  $('jpast').innerHTML = jp.map(e => {
    const dd = -dayDiff(e.d);
    const o = OUTS[`${e.r.slug}|${e.t}`];
    const chip = (o && o.r5 != null)
      ? `<div class="v" style="color:${o.r5 >= 0 ? 'var(--green)' : 'var(--red)'}">${o.r5 >= 0 ? '+' : ''}${o.r5}%</div><div class="s">5 days after</div>`
      : `<div class="v" style="color:var(--mut)">—</div><div class="s">syncing</div>`;
    return `<div class="wrow" data-slug="${e.r.slug}" data-mtab="h">
      <div class="wd">${dd}d ago<br><span style="font-weight:400">${fmtS(e.d)}</span></div>
      <div class="wmain"><div class="wname">${esc(e.r.company)}${plChip(e.r)}</div>
      <div class="wsub">${e.sh ? shFmt(e.sh)+' sh' : ''}${e.pct != null ? ' · '+e.pct+'% of company' : ''}</div></div>
      ${pills(e)}
      <div class="wnum">${chip}</div>
    </div>`;
  }).join('') || '<div class="empty" style="padding:16px 14px">no unlocks in the last 30 days</div>';

  drawStrip(up);
  drawLedger(up, past);
}
function drawStrip(up){
  let h = '<span class="snow" style="left:0%"></span>';
  up.filter(e => dayDiff(e.d) > 0 && dayDiff(e.d) <= WIN).forEach(e => {
    const fam = e.meta.fam;
    h += `<span class="sdot i-${fam}" style="left:${(dayDiff(e.d)/WIN*100).toFixed(1)}%" title="${esc(e.r.company)} · ${e.meta.lbl} · ${fmtM(e.d)}" data-slug="${e.r.slug}"></span>`;
  });
  $('strip').innerHTML = h;
  $('hzout').textContent = 'next ' + WIN + ' days';
  const end = new Date(T0.getTime() + WIN * 86400000);
  $('hzend').textContent = fmtS(iso(end));
}
function drawLedger(up, past){
  let list = TAB === 'up' ? up.filter(e => dayDiff(e.d) <= WIN) : past;
  if(Q) list = list.filter(e => e.r.company.toLowerCase().includes(Q));
  $('ledger').innerHTML = list.map(e => {
    const dd = dayDiff(e.d);
    const mv = mkt(e), dv = dov(e);
    const nm = Q ? esc(e.r.company).replace(new RegExp('(' + Q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&') + ')','ig'),'<mark>$1</mark>') : esc(e.r.company);
    return `<div class="lrow ${dd<0?'past':''}" data-slug="${e.r.slug}">
      <span class="ld">${fmtS(e.d)}</span>
      <span class="lco">${nm}${plChip(e.r)}</span>
      ${pills(e)}
      <span class="lnum">${mv != null ? crFmt(mv) : (crFmt(e.val) || (e.pct != null ? e.pct+'%' : shFmt(e.sh)))}</span>
      <span class="dot ${dv != null ? dovDot(dv) : ''}" style="${dv == null ? 'background:var(--line2)' : ''}" title="${dv != null ? dovLab(dv)+' daily volume' : 'volume data pending'}"></span>
    </div>`;
  }).join('') || '<div class="empty">nothing in this window — extend the horizon or clear the search</div>';
}
$('hz').addEventListener('input', e => { WIN = parseInt(e.target.value); render(); });
document.querySelectorAll('.fdot').forEach(c => c.onclick = () => {
  FAM_ON[c.dataset.f] = !FAM_ON[c.dataset.f];
  c.classList.toggle('off', !FAM_ON[c.dataset.f]);
  render();
});
document.querySelectorAll('.tab').forEach(b => b.onclick = () => {
  TAB = b.dataset.t;
  document.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === b));
  render();
});
$('mbToggle').onchange = e => { MB = e.target.checked; render(); };
$('search').oninput = e => { Q = e.target.value.trim().toLowerCase(); render(); };
render();
</script>
</body>
</html>"""

html = HTML.replace("__DATA__", json.dumps(payload, ensure_ascii=False)) \
           .replace("__STATS__", json.dumps(OUTCOME_STATS)) \
           .replace("__OUTS__", json.dumps(OUT_KEYED)) \
           .replace("__FUNDS__", json.dumps(FUND_COUNTS, ensure_ascii=False)) \
           .replace("__REG__", json.dumps(_slug_names, ensure_ascii=False)) \
           .replace("__GENERATED__", gen_label)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)
n_ev = sum(1 for r in records for e in r.get("events", []) if e["d"] and e["d"] >= today_iso)
print(f"[build] v4 pressure-board layout written ({len(html)//1024} KB), {n_ev} future events, "
      f"{len(FUND_COUNTS)} funds in registry, outcome stats: {OUTCOME_STATS}")
