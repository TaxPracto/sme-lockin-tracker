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
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unlock Radar — SME IPO lock-in expiries</title>
<meta name="description" content="Daily-refreshed calendar of anchor, pre-IPO and promoter lock-in expiries for Indian SME IPOs.">
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
body{background:var(--bg);color:var(--txt);font-family:"Instrument Sans",system-ui,sans-serif;font-size:15px;
  background-image:radial-gradient(1100px 500px at 15% -10%, rgba(179,111,0,.06), transparent 60%),
                   radial-gradient(900px 420px at 96% -4%, rgba(14,116,144,.05), transparent 55%);
  min-height:100vh; padding-bottom:60px}
.grain{position:fixed;inset:0;pointer-events:none;opacity:.05;z-index:99;mix-blend-mode:multiply;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 240 240' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
.wrap{max-width:1180px;margin:0 auto;padding:0 28px}
a{color:inherit;text-decoration:none}
h2{font-family:Fraunces,serif;font-weight:430;font-style:italic;font-size:22px;color:var(--mut2);margin-bottom:14px}
::selection{background:rgba(179,111,0,.22)}

.mast{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding:42px 0 22px;border-bottom:1.5px solid var(--line2);flex-wrap:wrap}
.kicker{font-size:11.5px;font-weight:600;letter-spacing:.24em;color:var(--mut);display:flex;align-items:center;gap:14px;animation:rise .6s .05s both}
.live{display:inline-flex;align-items:center;gap:6px;color:var(--green);letter-spacing:.14em;font-size:10.5px;font-weight:600}
.live i{width:7px;height:7px;border-radius:50%;background:var(--green);animation:blink 2.2s infinite}
h1{font-family:Fraunces,serif;font-weight:400;font-size:clamp(44px,7vw,74px);line-height:.98;margin:12px 0 10px;animation:rise .6s .12s both}
h1 em{font-style:italic;color:var(--amber)}
.sub{color:var(--mut2);max-width:600px;font-size:14px;line-height:1.7;animation:rise .6s .2s both}
.mast-right{text-align:right;animation:rise .6s .26s both}
.today-date{font-family:Fraunces,serif;font-style:italic;font-size:23px;color:var(--mut2)}
.updated{font-size:12px;color:var(--mut);margin-top:8px;line-height:1.9}
.updated a{color:var(--cyan);border-bottom:1px dotted rgba(14,116,144,.5);font-weight:500}
.updated b{font-family:var(--mono);font-weight:500}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}

.typebar{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0 4px;animation:rise .6s .3s both}
.tchip{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:600;letter-spacing:.08em;padding:8px 15px;background:var(--panel);border:1px solid var(--line2);border-radius:99px;cursor:pointer;color:var(--mut2);user-select:none;transition:all .15s;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.tchip i{width:9px;height:9px;border-radius:50%}
.tchip.off{opacity:.4;filter:grayscale(.6);box-shadow:none;background:transparent}
.tchip:hover{border-color:rgba(24,33,51,.3)}
.i-a30{background:var(--amber)}.i-a90{background:var(--cyan)}.i-pre{background:var(--violet)}.i-px{background:var(--coral)}

.stats{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line2);border-radius:16px;margin:18px 0 8px;overflow:hidden;background:var(--panel);box-shadow:0 1px 3px rgba(16,24,40,.05);animation:rise .6s .32s both}
.stat{padding:20px 22px;border-right:1px solid var(--line)}
.stat:last-child{border-right:0}
.stat .k{font-size:10.5px;font-weight:600;letter-spacing:.2em;color:var(--mut)}
.stat .v{font-family:var(--mono);font-size:31px;margin-top:8px;font-weight:600}
.stat .s{font-size:12px;color:var(--mut);margin-top:4px}
.stat.hot .v{color:var(--red)} .stat.warm .v{color:var(--amber)} .stat.cool .v{color:var(--cyan)}

.rail-wrap{margin-top:40px;animation:rise .6s .4s both}
.rail{display:flex;gap:14px;overflow-x:auto;padding:4px 2px 18px;scroll-snap-type:x mandatory;scrollbar-width:thin;scrollbar-color:var(--line2) transparent}
.card{min-width:222px;scroll-snap-align:start;background:var(--panel);border:1px solid var(--line2);border-radius:15px;padding:16px 17px 14px;transition:transform .22s,box-shadow .22s;display:flex;flex-direction:column;gap:9px;box-shadow:0 1px 3px rgba(16,24,40,.05)}
.card:hover{transform:translateY(-4px);box-shadow:0 8px 22px rgba(16,24,40,.12)}
.card.today{border-color:rgba(214,39,59,.5);animation:glow 2.6s infinite}
@keyframes glow{0%,100%{box-shadow:0 2px 10px rgba(214,39,59,.12)}50%{box-shadow:0 4px 24px rgba(214,39,59,.25)}}
.dbadge{font-size:11.5px;letter-spacing:.1em;color:var(--mut);display:flex;justify-content:space-between;align-items:center;font-family:var(--mono)}
.dbadge b{font-size:17px;font-weight:600;color:var(--txt)}
.card.today .dbadge b{color:var(--red)}
.card.soon .dbadge b{color:var(--amber)}
.cname{font-size:14px;line-height:1.4;min-height:40px;font-weight:600}
.pill{display:inline-block;font-size:10.5px;letter-spacing:.08em;padding:3px 10px;border-radius:99px;font-weight:700}
.p30{background:var(--amber-bg);color:var(--amber)}
.p90{background:var(--cyan-bg);color:var(--cyan)}
.p6m{background:var(--violet-bg);color:var(--violet)}
.ppx{background:var(--coral-bg);color:var(--coral)}
.pmb{background:#E8ECF5;color:#4A5A7A}
.cnums{display:flex;justify-content:space-between;border-top:1px solid var(--line);padding-top:10px;font-size:13px;font-family:var(--mono);font-weight:500}
.cnums span{display:block;font-family:"Instrument Sans",sans-serif;font-size:9.5px;font-weight:600;color:var(--mut);letter-spacing:.12em;margin-top:3px}

.cal-wrap{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:34px;animation:rise .6s .46s both}
.cal{background:var(--panel);border:1px solid var(--line);border-radius:15px;padding:18px 20px;box-shadow:0 1px 3px rgba(16,24,40,.04)}
.cal h3{font-family:Fraunces,serif;font-style:italic;font-weight:430;font-size:16px;color:var(--mut2);margin-bottom:12px}
.cal-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(31px,1fr));gap:5px}
.day{aspect-ratio:1;border-radius:8px;border:1px solid transparent;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;font-size:11px;color:var(--mut);font-family:var(--mono)}
.day.has{border-color:var(--line2);background:var(--panel2);cursor:pointer;color:var(--txt);font-weight:600}
.day.has:hover{border-color:rgba(24,33,51,.35)}
.day.today{border-color:var(--red);color:var(--red);font-weight:700}
.dots{display:flex;gap:2px}
.dot{width:4.5px;height:4.5px;border-radius:50%}

.ledger-wrap{margin-top:44px;animation:rise .6s .5s both}
.ledger-head{display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;margin-bottom:16px}
.controls{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.tabs{display:flex;border:1px solid var(--line2);border-radius:10px;overflow:hidden;background:var(--panel)}
.tab{padding:8px 16px;font-size:11.5px;font-weight:600;letter-spacing:.1em;color:var(--mut);cursor:pointer;background:transparent;border:0;font-family:inherit}
.tab.on{background:var(--txt);color:#fff}
.mb-toggle{display:flex;gap:7px;align-items:center;font-size:12px;font-weight:500;color:var(--mut2);cursor:pointer}
.mb-toggle input{accent-color:var(--amber)}
#search{background:var(--panel);border:1px solid var(--line2);border-radius:10px;color:var(--txt);font-family:inherit;font-size:13px;padding:9px 14px;width:200px;outline:none;box-shadow:0 1px 2px rgba(16,24,40,.04)}
#search:focus{border-color:var(--amber)}
.lgroup{margin-bottom:6px}
.ldate{font-size:11.5px;font-weight:700;letter-spacing:.16em;color:var(--mut);padding:18px 4px 8px;display:flex;gap:10px;align-items:center}
.ldate.today-l{color:var(--red)}
.lrow{display:grid;grid-template-columns:52px 1fr 112px 110px 110px 30px;gap:10px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:13px 16px;margin-bottom:7px;transition:box-shadow .18s,transform .18s;box-shadow:0 1px 2px rgba(16,24,40,.04)}
.lrow:hover{transform:translateX(3px);box-shadow:0 4px 14px rgba(16,24,40,.1);border-color:var(--line2)}
.lrow.past{opacity:.55}
.lrow .dd{font-family:var(--mono);font-size:17px;font-weight:600;color:var(--mut2)}
.lrow .dd span{display:block;font-size:9px;letter-spacing:.18em;color:var(--mut);font-weight:500}
.lrow .co{font-size:14px;font-weight:600;line-height:1.35}
.lrow .co span{display:block;font-size:11px;color:var(--mut);margin-top:2px;font-weight:400}
.num{text-align:right;font-size:13px;font-family:var(--mono);font-weight:500}
.num span{display:block;font-family:"Instrument Sans",sans-serif;font-size:9px;font-weight:600;color:var(--mut);letter-spacing:.14em;margin-top:2px}
.go{color:var(--mut);font-size:15px;text-align:center}
.lrow:hover .go{color:var(--cyan)}
.empty{color:var(--mut);padding:30px 4px;font-size:13px}
mark{background:rgba(179,111,0,.25);color:var(--txt);border-radius:3px}

.mback{position:fixed;inset:0;background:rgba(26,33,48,.45);backdrop-filter:blur(6px);display:none;z-index:200;align-items:center;justify-content:center;padding:20px}
.mback.on{display:flex}
.mcard{background:var(--panel);border:1px solid var(--line2);border-radius:18px;max-width:760px;width:100%;max-height:88vh;overflow-y:auto;padding:28px 30px 24px;animation:mup .28s cubic-bezier(.2,.9,.3,1);scrollbar-width:thin;box-shadow:0 24px 60px rgba(16,24,40,.25)}
@keyframes mup{from{opacity:0;transform:translateY(26px) scale(.98)}to{opacity:1;transform:none}}
.mhead{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;border-bottom:1px solid var(--line);padding-bottom:14px}
.mhead h3{font-family:Fraunces,serif;font-style:italic;font-weight:430;font-size:25px;line-height:1.2}
.mhead .msub{font-size:11.5px;color:var(--mut);margin-top:6px;line-height:1.9;font-family:var(--mono)}
.mx{background:var(--panel);border:1px solid var(--line2);color:var(--mut2);border-radius:9px;font-family:inherit;font-size:12px;font-weight:600;padding:6px 11px;cursor:pointer}
.mx:hover{border-color:var(--red);color:var(--red)}
.mgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:16px 0 4px}
.mstat{background:var(--panel2);border:1px solid var(--line);border-radius:11px;padding:11px 13px}
.mstat .k{font-size:9.5px;font-weight:700;letter-spacing:.16em;color:var(--mut)}
.mstat .v{font-family:var(--mono);font-size:14.5px;font-weight:600;margin-top:5px}
.mstat .v small{font-size:10px;color:var(--mut);font-weight:400}
.msec{font-size:10.5px;font-weight:700;letter-spacing:.22em;color:var(--mut);margin:20px 0 10px}
.mev{border:1px solid var(--line);border-left-width:3.5px;border-radius:11px;padding:12px 15px;margin-bottom:9px;background:#FDFCFA}
.mev.b30{border-left-color:var(--amber)} .mev.b90{border-left-color:var(--cyan)}
.mev.bpre{border-left-color:var(--violet)} .mev.bpx{border-left-color:var(--coral)}
.mev .top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.mev .top b{font-size:14px;font-weight:600}
.mev .num2{font-size:12.5px;color:var(--mut2);font-family:var(--mono)}
.mev .how{font-size:12.5px;color:var(--mut2);line-height:1.9;margin-top:8px;border-top:1px dashed var(--line2);padding-top:8px}
.mev .how .fl{display:block}
.mev .how b{color:var(--txt);font-weight:600;font-family:var(--mono);font-size:12px}
.mev .how .lbl{display:inline-block;min-width:44px;font-weight:700;color:var(--mut);font-size:10.5px;letter-spacing:.1em}
.mnote{font-size:11.5px;color:var(--mut);line-height:1.8;margin-top:16px;border-top:1px solid var(--line);padding-top:12px}
.mbtns{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap}
.mbtn{border-radius:10px;padding:11px 18px;font-family:inherit;font-size:12.5px;font-weight:700;letter-spacing:.04em;cursor:pointer;text-align:center}
.mbtn.primary{background:var(--txt);color:#fff;border:0}
.mbtn.primary:hover{background:#000}
.mbtn.ghost{background:transparent;border:1px solid var(--line2);color:var(--mut2)}
.mbtn.ghost:hover{border-color:var(--txt);color:var(--txt)}
@media(max-width:700px){.mgrid{grid-template-columns:1fr 1fr}.mcard{padding:20px 18px}}

footer{border-top:1px solid var(--line2);margin-top:52px;padding-top:22px;font-size:12px;color:var(--mut);line-height:1.9;display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}
footer b{color:var(--mut2);font-weight:600}
@media(max-width:860px){
  .stats{grid-template-columns:1fr 1fr}
  .stat:nth-child(2){border-right:0}
  .stat{border-bottom:1px solid var(--line)}
  .cal-wrap{grid-template-columns:1fr}
  .lrow{grid-template-columns:44px 1fr 100px 30px}
  .lrow .num.hm{display:none}
  .mast{padding-top:30px}
  .mast-right{text-align:left}
}
</style>
</head>
<body>
<div class="grain"></div>
<div class="wrap">

<header class="mast">
  <div>
    <div class="kicker">SME IPO · LOCK-IN EXPIRIES <span class="live"><i></i>DAILY 07:00 IST</span></div>
    <h1>Unlock <em>Radar</em></h1>
    <div class="sub">Anchor tranches, pre-IPO holder windows and promoter releases on BSE SME &amp; NSE Emerge — who can sell, when, and how much of the company is unlocking. Click any company for the full math.</div>
  </div>
  <div class="mast-right">
    <div class="today-date" id="mastDate"></div>
    <div class="updated">data as of <b>__GENERATED__</b><br>
    <a href="lockins.ics">calendar feed (.ics)</a> · <a href="data.json">raw json</a></div>
  </div>
</header>

<div class="typebar" id="typebar">
  <div class="tchip" data-f="a30"><i class="i-a30"></i>30D ANCHOR</div>
  <div class="tchip" data-f="a90"><i class="i-a90"></i>90D ANCHOR</div>
  <div class="tchip" data-f="pre"><i class="i-pre"></i>6M PRE-IPO <small style="opacity:.65">est.</small></div>
  <div class="tchip" data-f="px"><i class="i-px"></i>PROMOTER 1Y/2Y <small style="opacity:.65">est.</small></div>
</div>

<section class="stats" id="stats"></section>
<section class="rail-wrap"><h2>Up next</h2><div class="rail" id="rail"></div></section>
<section class="cal-wrap" id="cals"></section>

<section class="ledger-wrap">
  <div class="ledger-head">
    <h2>The ledger</h2>
    <div class="controls">
      <div class="tabs" id="tabs">
        <button class="tab on" data-t="up">UPCOMING</button>
        <button class="tab" data-t="past">PAST</button>
        <button class="tab" data-t="all">ALL</button>
      </div>
      <label class="mb-toggle"><input type="checkbox" id="mbToggle"> + Mainboard (anchor only)</label>
      <input id="search" placeholder="search company…" autocomplete="off">
    </div>
  </div>
  <div id="ledger"></div>
</section>

<footer>
  <div><b>Unlock Radar v2</b> · data: Chittorgarh.com + SEBI ICDR rules · refreshed daily by GitHub Actions.<br>
  Anchor: 50% each at 30/90 days · Pre-IPO: non-promoter holders at 6 months (est.) · Promoter: excess over 20% MPC at 1yr/2yr (est.).</div>
  <div>Events marked <b>est.</b> are computed, not exchange-confirmed — verify before acting.<br>
  For research &amp; information only — <b>not investment advice</b>.</div>
</footer>

</div>
<div class="mback" id="mback"><div class="mcard" id="mcard"></div></div>
<script>
const DATA = __DATA__;
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
const fmtS = s => { const d = pd(s); return `${DOW[d.getDay()]} · ${String(d.getDate()).padStart(2,'0')} ${MON[d.getMonth()]}`; };
function shFmt(n){
  if(n == null || n === 0) return '—';
  if(n >= 1e7) return (n/1e7).toFixed(2).replace(/\.?0+$/,'') + ' Cr';
  if(n >= 1e5) return (n/1e5).toFixed(2).replace(/\.?0+$/,'') + ' L';
  return n.toLocaleString('en-IN');
}
const crFmt = v => v == null ? null : '₹' + (v >= 100 ? Math.round(v).toLocaleString('en-IN') : v.toFixed(1)) + ' cr';
const esc = s => s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const TYPE = {
  A30:{lbl:'30D', cls:'p30', fam:'a30'}, A90:{lbl:'90D', cls:'p90', fam:'a90'},
  PRE6M:{lbl:'6M PRE-IPO', cls:'p6m', fam:'pre'},
  PX1Y:{lbl:'1Y PROM', cls:'ppx', fam:'px'}, PX2Y:{lbl:'2Y PROM', cls:'ppx', fam:'px'}
};
const FAM_ON = {a30:true, a90:true, pre:true, px:true};
let TAB='up', MB=false, Q='';

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
function sizeMain(e){ return crFmt(e.val) || (e.pct != null ? e.pct + '% cap' : shFmt(e.sh)); }
function sizeLbl(e){ return e.val != null ? 'AT ISSUE PX' : (e.pct != null ? 'OF CAPITAL' + (e.est?' · EST':'') : 'SHARES' + (e.est?' · EST':'')); }
function pills(e){
  let h = `<span class="pill ${e.meta.cls}">${e.meta.lbl}</span>`;
  if(e.r.category !== 'SME') h += ` <span class="pill pmb">MB</span>`;
  return h;
}
function subLine(r){
  const bits = [`allotted ${r.anchor_allotment_date || '—'}`];
  if(r.nonprom_pre_shares) bits.push(`pre-IPO non-prom: ${shFmt(r.nonprom_pre_shares)} sh${r.nonprom_pre_pct_of_post ? ' · ' + r.nonprom_pre_pct_of_post + '% cap' : ''}`);
  else if(r.pct_of_issue) bits.push(r.pct_of_issue + '% of issue');
  return bits.join(' · ');
}
const $ = id => document.getElementById(id);
const TLONG = {A30:'30-day anchor unlock', A90:'90-day anchor unlock', PRE6M:'Pre-IPO holders unlock (6M)', PX1Y:'Promoter release (1 year)', PX2Y:'Promoter release (2 years)'};
const BCLS = {A30:'b30', A90:'b90', PRE6M:'bpre', PX1Y:'bpx', PX2Y:'bpx'};
const nfmt = n => n == null ? '—' : n.toLocaleString('en-IN');
const line = (lbl, txt) => `<span class="fl"><span class="lbl">${lbl}</span> ${txt}</span>`;

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
      ? `<b>${nfmt(r.pre_shares)}</b> pre-issue sh × (100 − ${r.prom_pre_pct}%) = <b>${nfmt(r.nonprom_pre_shares)}</b> sh${r.nonprom_pre_pct_of_post ? ` (${r.nonprom_pre_pct_of_post}% cap)` : ''}`
      : `pending — shareholding data syncs on next run`;
    return line('QTY', q) +
           line('DATE', `allotment ${fmtM(allot)} + 6 months = <b>${fmtM(e.d)}</b> (est., ±few days)`);
  }
  const excPct = r.prom_post_pct != null ? (r.prom_post_pct - 20).toFixed(2) : null;
  if(e.t === 'PX1Y'){
    const q = excPct ? `(${r.prom_post_pct}% − 20% MPC) = ${excPct}% × post-issue = <b>${nfmt(e.sh != null ? (phased ? e.sh * 2 : e.sh) : null)}</b> sh excess${phased ? '; <b>50%</b> releases now' : '; <b>100%</b> releases now'}` : 'pending shareholding data';
    return line('QTY', q) +
           line('DATE', `allotment ${fmtM(allot)} + 12 months = <b>${fmtM(e.d)}</b> (est.)`) +
           line('RULE', phased ? 'listed on/after 08-Mar-2025 → phased 50/50 release' : 'listed before 08-Mar-2025 → single release at 1yr');
  }
  if(e.t === 'PX2Y'){
    return line('QTY', `remaining <b>50%</b> of promoter excess = <b>${nfmt(e.sh)}</b> sh (20% MPC stays locked 3yrs)`) +
           line('DATE', `allotment ${fmtM(allot)} + 24 months = <b>${fmtM(e.d)}</b> (est.)`);
  }
  return '';
}
function openModal(slug){
  const r = DATA.records.find(x => x.slug === slug);
  if(!r) return;
  const evs = (r.events || []).slice().sort((a,b) => a.d.localeCompare(b.d));
  const evHtml = evs.map(e => {
    const dd = dayDiff(e.d);
    const when = dd === 0 ? 'TODAY' : dd > 0 ? `D-${dd}` : `${-dd}d ago`;
    const size = [e.sh ? shFmt(e.sh) + ' sh' : null, e.pct != null ? e.pct + '% of capital' : null, e.val != null ? crFmt(e.val) + ' at issue px' : null].filter(Boolean).join(' · ') || 'size n/a';
    return `<div class="mev ${BCLS[e.t]}">
      <div class="top"><b>${TLONG[e.t]}</b><span class="num2">${fmtL(e.d)} · ${when}</span></div>
      <div class="num2" style="margin-top:5px">${size}</div>
      <div class="how">${explain(e, r)}</div></div>`;
  }).join('') || '<div class="empty">no events computed</div>';
  const mpc = r.post_shares ? Math.round(r.post_shares * 0.2) : null;
  $('mcard').innerHTML = `
    <div class="mhead"><div>
      <h3>${esc(r.company)}</h3>
      <div class="msub">${r.category}${r.nse_symbol ? ' · NSE ' + esc(String(r.nse_symbol)) : ''}${r.bse_code ? ' · BSE ' + r.bse_code : ''}${r.isin ? ' · ' + esc(String(r.isin)) : ''}<br>
      allotted ${r.anchor_allotment_date || '—'} · listed ${r.listing_date || '—'}</div>
    </div><button class="mx" onclick="closeModal()">✕ esc</button></div>
    <div class="mgrid">
      <div class="mstat"><div class="k">PRE-ISSUE CAPITAL</div><div class="v">${shFmt(r.pre_shares)} <small>sh</small></div></div>
      <div class="mstat"><div class="k">POST-ISSUE CAPITAL</div><div class="v">${shFmt(r.post_shares)} <small>sh</small></div></div>
      <div class="mstat"><div class="k">PROMOTER PRE → POST</div><div class="v">${r.prom_pre_pct != null ? r.prom_pre_pct + '%' : '—'} → ${r.prom_post_pct != null ? r.prom_post_pct + '%' : '—'}</div></div>
      <div class="mstat"><div class="k">NON-PROM PRE-IPO</div><div class="v">${shFmt(r.nonprom_pre_shares)} <small>${r.nonprom_pre_pct_of_post ? '· ' + r.nonprom_pre_pct_of_post + '% cap' : ''}</small></div></div>
      <div class="mstat"><div class="k">ANCHOR ALLOTMENT</div><div class="v">${shFmt(r.anchor_shares)} <small>${r.anchor_investment_cr ? '· ₹' + r.anchor_investment_cr + ' cr' : ''}</small></div></div>
      <div class="mstat"><div class="k">20% MPC (3YR LOCK)</div><div class="v">${shFmt(mpc)} <small>sh</small></div></div>
    </div>
    <div class="msec">UNLOCK TIMELINE — QUANTITY &amp; DATE MATH</div>
    ${evHtml}
    <div class="mnote">Anchor dates are exchange-published. "est." events are computed from prospectus shareholding + SEBI ICDR rules — verify against the exchange listing circular before acting. AIF/VC exemptions and ESOPs can change actual free-float.</div>
    <div class="mbtns">
      ${r.url ? `<a class="mbtn primary" href="${r.url}" target="_blank" rel="noopener">Chittorgarh page ↗</a>` : ''}
      <button class="mbtn ghost" onclick="closeModal()">Close</button>
    </div>`;
  $('mback').classList.add('on');
  document.body.style.overflow = 'hidden';
}
function closeModal(){
  $('mback').classList.remove('on');
  document.body.style.overflow = '';
}
document.addEventListener('click', ev => {
  const t = ev.target.closest('[data-slug]');
  if(t){ ev.preventDefault(); openModal(t.dataset.slug); return; }
  if(ev.target.id === 'mback') closeModal();
});
document.addEventListener('keydown', ev => { if(ev.key === 'Escape') closeModal(); });

function render(){
  const evs = events();
  const up = evs.filter(e => dayDiff(e.d) >= 0).sort((a,b) => a.d.localeCompare(b.d) || (b.pct||0)-(a.pct||0) || (b.val||0)-(a.val||0));
  const past = evs.filter(e => dayDiff(e.d) < 0).sort((a,b) => b.d.localeCompare(a.d));
  $('mastDate').textContent = fmtL(iso(T0));

  const tC = up.filter(e => dayDiff(e.d) === 0);
  const w7 = up.filter(e => dayDiff(e.d) <= 7);
  const m30 = up.filter(e => dayDiff(e.d) <= 30);
  const big30 = m30.reduce((mx,e) => (e.pct||0) > (mx.pct||0) ? e : mx, {});
  $('stats').innerHTML = `
    <div class="stat hot"><div class="k">OPENING TODAY</div><div class="v">${tC.length}</div>
      <div class="s">${tC.length ? tC.map(e=>e.meta.lbl).join(' · ') : 'quiet session'}</div></div>
    <div class="stat warm"><div class="k">NEXT 7 DAYS</div><div class="v">${w7.length}</div><div class="s">unlock events</div></div>
    <div class="stat cool"><div class="k">NEXT 30 DAYS</div><div class="v">${m30.length}</div><div class="s">unlock events</div></div>
    <div class="stat"><div class="k">BIGGEST · 30D</div><div class="v">${big30.pct ? big30.pct + '%' : '—'}</div>
      <div class="s">${big30.r ? esc(big30.r.company).slice(0,26) + ' · ' + big30.meta.lbl : 'of capital unlocking'}</div></div>`;

  $('rail').innerHTML = up.slice(0, 14).map(e => {
    const dd = dayDiff(e.d);
    const cls = dd === 0 ? 'today' : (dd <= 7 ? 'soon' : '');
    return `<a class="card ${cls}" href="#" data-slug="${e.r.slug}">
      <div class="dbadge"><b>${dd === 0 ? 'TODAY' : 'D-' + dd}</b><span>${fmtS(e.d)}</span></div>
      <div class="cname">${esc(e.r.company)}</div>
      <div>${pills(e)}</div>
      <div class="cnums">
        <div>${sizeMain(e) || '—'}<span>${sizeLbl(e)}</span></div>
        <div>${shFmt(e.sh)}<span>SHARES</span></div>
      </div></a>`;
  }).join('') || '<div class="empty">nothing on the radar for these filters</div>';

  const byDay = {};
  evs.forEach(e => { (byDay[e.d] = byDay[e.d] || []).push(e); });
  $('cals').innerHTML = [0, 1].map(off => {
    const first = new Date(T0.getFullYear(), T0.getMonth() + off, 1);
    const dim = new Date(first.getFullYear(), first.getMonth() + 1, 0).getDate();
    let cells = '';
    for(let d = 1; d <= dim; d++){
      const ds = iso(new Date(first.getFullYear(), first.getMonth(), d));
      const es = byDay[ds] || [];
      const dots = es.slice(0,3).map(e => `<i class="dot i-${e.meta.fam === 'px' ? 'px' : e.meta.fam === 'pre' ? 'pre' : e.t === 'A30' ? 'a30' : 'a90'}"></i>`).join('');
      cells += `<div class="day ${es.length?'has':''} ${ds===iso(T0)?'today':''}" ${es.length?`onclick="jump('${ds}')"`:''} title="${es.length ? es.length + ' unlock(s)' : ''}">
        <span>${d}</span><span class="dots">${dots}</span></div>`;
    }
    return `<div class="cal"><h3>${MON[first.getMonth()]} ${first.getFullYear()}</h3><div class="cal-grid">${cells}</div></div>`;
  }).join('');

  let list = TAB === 'up' ? up : TAB === 'past' ? past : up.concat(past);
  if(Q) list = list.filter(e => e.r.company.toLowerCase().includes(Q));
  const groups = {};
  list.forEach(e => { (groups[e.d] = groups[e.d] || []).push(e); });
  const keys = Object.keys(groups);
  if(TAB === 'up') keys.sort(); else if(TAB === 'past') keys.sort().reverse();
  $('ledger').innerHTML = keys.map(d => {
    const dd = dayDiff(d);
    const label = dd === 0 ? 'TODAY — ' + fmtL(d) : dd === 1 ? 'TOMORROW — ' + fmtL(d) : fmtL(d);
    const rows = groups[d].map(e => {
      const day = pd(d);
      const nm = Q ? esc(e.r.company).replace(new RegExp('(' + Q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&') + ')','ig'),'<mark>$1</mark>') : esc(e.r.company);
      return `<a class="lrow ${dd<0?'past':''}" id="d${d}" href="#" data-slug="${e.r.slug}">
        <div class="dd">${String(day.getDate()).padStart(2,'0')}<span>${MON[day.getMonth()].toUpperCase()}</span></div>
        <div class="co">${nm}<span>${subLine(e.r)}</span></div>
        <div>${pills(e)}</div>
        <div class="num hm">${shFmt(e.sh)}<span>SHARES FREE${e.est ? ' · EST' : ''}</span></div>
        <div class="num">${e.pct != null ? e.pct + '%' : (crFmt(e.val) || '—')}<span>${e.pct != null ? 'OF CAPITAL' : 'AT ISSUE PX'}</span></div>
        <div class="go">ⓘ</div></a>`;
    }).join('');
    return `<div class="lgroup"><div class="ldate ${dd===0?'today-l':''}">${label}<span>· ${groups[d].length}</span></div>${rows}</div>`;
  }).join('') || '<div class="empty">no matches — clear search or switch tabs/filters</div>';
}
function jump(ds){
  TAB = dayDiff(ds) >= 0 ? 'up' : 'past';
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('on', b.dataset.t === TAB));
  render();
  const el = document.getElementById('d' + ds);
  if(el) el.scrollIntoView({behavior:'smooth', block:'center'});
}
document.querySelectorAll('.tchip').forEach(c => c.onclick = () => {
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
           .replace("__GENERATED__", gen_label)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)
n_ev = sum(1 for r in records for e in r.get("events", []) if e["d"] and e["d"] >= today_iso)
print(f"[build] v3 light theme written ({len(html)//1024} KB), {n_ev} future events")
